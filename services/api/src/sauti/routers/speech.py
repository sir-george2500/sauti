"""Speech endpoints — stubbed backend, shape-final.

Upload flow (MVP local storage standing in for signed S3 URLs):
POST /speech/upload-url -> {upload_url, audio_ref}; the client PUTs the blob to
upload_url (public, like a signed URL); POST /speech/score scores it.
GET /tts/{item_id} and GET /speech/audio/{ref} are public — they are used as
<audio> src and can't carry an Authorization header.
"""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select

from sauti.deps import CurrentUser, DbDep, SettingsDep
from sauti.errors import ApiError
from sauti.models import Item
from sauti.schemas.common import PronReport
from sauti.schemas.learning import SpeechScoreIn, UploadUrlIn, UploadUrlOut

router = APIRouter(tags=["speech"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
SAFE_REF = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

AUDIO_MEDIA_TYPES = {
    "wav": "audio/wav", "webm": "audio/webm", "ogg": "audio/ogg",
    "mp3": "audio/mpeg", "m4a": "audio/mp4",
}


def _media_type(ref: str) -> str:
    return AUDIO_MEDIA_TYPES.get(ref.rsplit(".", 1)[-1], "application/octet-stream")


@router.post("/speech/upload-url")
async def upload_url(body: UploadUrlIn, user: CurrentUser, settings: SettingsDep, request: Request) -> UploadUrlOut:
    speech = request.app.state.speech_gateway
    ref = speech.new_upload_ref(body.content_type)
    return UploadUrlOut(
        upload_url=f"{settings.app_base_url}/api/v1/speech/upload/{ref}",
        audio_ref=ref,
    )


@router.put("/speech/upload/{ref}", status_code=204)
async def upload(ref: str, request: Request) -> None:
    # Public like a signed URL, so the ref must be one WE issued (unguessable
    # uuid4 hex, TTL-bound) — otherwise anyone could mint refs and fill disk.
    if not SAFE_REF.match(ref) or not ref.startswith("user-"):
        raise ApiError(404, "NOT_FOUND", "Unknown upload target")
    speech = request.app.state.speech_gateway
    if not speech.upload_ref_valid(ref):
        raise ApiError(404, "NOT_FOUND", "Unknown upload target")
    # Reject oversize early via Content-Length, then stream with a hard cap so
    # a chunked body can't balloon memory before the size check.
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise ApiError(413, "TOO_LARGE", "Audio upload too large")
    size = 0
    chunks: list[bytes] = []
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise ApiError(413, "TOO_LARGE", "Audio upload too large")
        chunks.append(chunk)
    speech.save_upload(ref, b"".join(chunks))


@router.post("/speech/score")
async def score(body: SpeechScoreIn, user: CurrentUser, db: DbDep, request: Request) -> PronReport:
    item = await db.scalar(select(Item).where(Item.id == body.item_id))
    if item is None:
        raise ApiError(404, "NOT_FOUND", "Unknown item")
    speech = request.app.state.speech_gateway
    return speech.score(body.audio_ref, str(item.id), item.phoneme_ref or {})


@router.get("/tts/{item_id}")
async def tts(item_id: uuid.UUID, db: DbDep, request: Request) -> RedirectResponse:
    item = await db.scalar(select(Item).where(Item.id == item_id))
    if item is None:
        raise ApiError(404, "NOT_FOUND", "Unknown item")
    speech = request.app.state.speech_gateway
    ref = speech.tts(item.sentence, voice=str(item.voice_id or ""), cache_key=item.id.hex)
    return RedirectResponse(url=f"/api/v1/speech/audio/{ref}", status_code=302)


@router.get("/speech/audio/{ref}")
async def audio(ref: str, request: Request) -> FileResponse:
    if not SAFE_REF.match(ref):
        raise ApiError(404, "NOT_FOUND", "Unknown audio")
    path = request.app.state.speech_gateway.audio_path(ref)
    if path is None:
        raise ApiError(404, "NOT_FOUND", "Unknown audio")
    return FileResponse(path, media_type=_media_type(ref))
