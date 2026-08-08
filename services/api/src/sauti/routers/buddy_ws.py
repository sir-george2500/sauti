"""WS /ws/buddy — Mwarimu, the floating study buddy.

Client sends {text}; the server streams frames:
  {type: "buddy",       id?, text, gloss?}             — the reply (always first)
  {type: "action",      action: {kind, href, label}}   — zero or more guidance chips
  {type: "buddy_audio", id, audio_url}                 — the spoken reply, when ready
  {type: "error",       text}                          — user-safe, never internals

The reply TEXT is never blocked or delayed by synthesis: the bubble goes out
first and `buddy_audio` follows, matched to it by `id`. An `id` on the reply is
a PROMISE that a clip was ordered — the UI waits on it — so a turn that never
started synthesizing sends none. If the voice service is down or synthesis
fails, no audio frame arrives and the chat is unaffected.

Auth: access token as ?token= query param — the same scheme the conversation
socket uses (browsers cannot set WS headers).
"""
from __future__ import annotations

import uuid

import jwt as pyjwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from sauti.models import Profile, User
from sauti.security import parse_access_token
from sauti.services.buddy import (
    RATE_LIMITED_TEXT,
    UNAVAILABLE_TEXT,
    BuddyOrchestrator,
)

router = APIRouter(tags=["buddy"])

WS_UNAUTHORIZED = 4401
WS_NOT_FOUND = 4404


@router.websocket("/ws/buddy")
async def buddy_ws(websocket: WebSocket) -> None:
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
        profile = await db.scalar(select(Profile).where(Profile.user_id == user_id))
        if user is None or profile is None:
            # No profile = no course = nothing to be a study buddy about.
            await websocket.close(code=WS_NOT_FOUND)
            return

        buddy = BuddyOrchestrator(
            db=db,
            llm=app.state.llm_client,
            user_id=user_id,
            profile=profile,
            sessionmaker=maker,  # usage metering writes on its own session
            speech=app.state.speech_gateway,
            base_url=settings.app_base_url,
        )
        await buddy.open()  # status context: read ONCE, reused every turn

        limiter = app.state.rate_limiter
        try:
            while True:
                payload = await websocket.receive_json()
                text = (payload.get("text") or "").strip() if isinstance(payload, dict) else ""
                if not text:
                    await websocket.send_json(
                        {"type": "error", "text": "Send me some words: {text: \"...\"}"}
                    )
                    continue
                if not limiter.check(f"buddy:u:{user_id}", settings.rate_limit_buddy_max):
                    # Friendly and in character — never a raw 429 or a closed socket.
                    await websocket.send_json({"type": "error", "text": RATE_LIMITED_TEXT})
                    continue
                try:
                    await buddy.turn(text, websocket.send_json)
                except WebSocketDisconnect:
                    raise
                except Exception:  # noqa: BLE001 — the LLM is down; degrade warmly
                    await db.rollback()
                    try:
                        # No `id`: an id promises a clip, and this turn never
                        # got far enough to synthesize one. The UI shows the
                        # bubble with no play control rather than a spinner
                        # that waits forever.
                        await websocket.send_json({"type": "buddy", "text": UNAVAILABLE_TEXT})
                    except RuntimeError:
                        return  # client vanished mid-turn — nothing left to tell
                    continue
        except WebSocketDisconnect:
            return
