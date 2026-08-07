"""WS /ws/conversation/{scenario_id}

Client sends {text} or {audio_ref}; server streams frames
{type: partner|coach|goal|error, text, gloss?, coach?, audio_url?}.
Auth: access token as ?token= query param (browsers can't set WS headers).
"""
from __future__ import annotations

import uuid

import jwt as pyjwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from sauti.models import Profile, Scenario, User
from sauti.security import parse_access_token
from sauti.services.conversation import ConversationOrchestrator
from sauti.speech.gateway import SpeechUnavailableError

router = APIRouter(tags=["conversation"])

WS_UNAUTHORIZED = 4401
WS_NOT_FOUND = 4404

# Learner turns are a sentence or two; a hard cap keeps a hostile client from
# pumping megabyte frames into the (paid) LLM context.
MAX_TEXT_CHARS = 1000


@router.websocket("/ws/conversation/{scenario_id}")
async def conversation_ws(websocket: WebSocket, scenario_id: uuid.UUID) -> None:
    app = websocket.app
    settings = app.state.settings

    token = websocket.query_params.get("token", "")
    try:
        claims = parse_access_token(settings, token)
        user_id = uuid.UUID(claims["sub"])
    except (pyjwt.PyJWTError, KeyError, ValueError):
        await websocket.close(code=WS_UNAUTHORIZED)
        return

    await websocket.accept()

    maker = app.state.sessionmaker
    async with maker() as db:
        user = await db.scalar(select(User).where(User.id == user_id))
        scenario = await db.scalar(select(Scenario).where(Scenario.id == scenario_id))
        if user is None or scenario is None:
            await websocket.close(code=WS_NOT_FOUND)
            return
        profile = await db.scalar(select(Profile).where(Profile.user_id == user_id))
        cefr = (profile.placed_level if profile else None) or "A1"

        orchestrator = ConversationOrchestrator(
            db=db,
            llm=app.state.llm_client,
            speech=app.state.speech_gateway,
            base_url=settings.app_base_url,
        )
        conv = await orchestrator.open(user_id, scenario)
        # Scripted opener (persona greets first) from persona.opening_line —
        # zero LLM calls; a no-op when the scenario has none. Best-effort.
        await orchestrator.send_opener(conv, scenario, websocket.send_json)

        limiter = app.state.rate_limiter
        try:
            while True:
                payload = await websocket.receive_json()
                if not limiter.check(
                    f"conv:u:{user_id}", settings.rate_limit_conversation_max
                ):
                    await websocket.send_json(
                        {"type": "error", "text": "Slow down a moment — too many messages."}
                    )
                    continue
                text = (payload.get("text") or "").strip() if isinstance(payload, dict) else ""
                audio_ref = payload.get("audio_ref") if isinstance(payload, dict) else None
                if not text and audio_ref:
                    # Mic input arrives as an audio_ref (stub accepts "stub:mic-take").
                    try:
                        text = await app.state.speech_gateway.stt(str(audio_ref), "rw")
                    except (SpeechUnavailableError, FileNotFoundError):
                        await websocket.send_json(
                            {
                                "type": "error",
                                "text": "We couldn't hear that take — speech recognition "
                                "is unavailable right now. Type your reply instead.",
                            }
                        )
                        continue
                if not text:
                    await websocket.send_json(
                        {"type": "error", "text": "Send {text} or {audio_ref}."}
                    )
                    continue
                if len(text) > MAX_TEXT_CHARS:
                    await websocket.send_json(
                        {"type": "error", "text": "That message is too long — keep it short."}
                    )
                    continue
                try:
                    # Frames are streamed as they become ready (partner text
                    # first; audio + coach follow) — not buffered to turn end.
                    await orchestrator.turn(conv, scenario, cefr, text, websocket.send_json)
                except WebSocketDisconnect:
                    raise
                except Exception as exc:  # degrade gracefully — never break the socket
                    await db.rollback()
                    try:
                        await websocket.send_json(
                            {"type": "error", "text": f"AI_ERROR: {type(exc).__name__}"}
                        )
                    except RuntimeError:
                        return  # client vanished mid-turn — nothing left to tell
                    continue
        except WebSocketDisconnect:
            return
