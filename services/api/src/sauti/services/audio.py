"""Bulk cached-audio resolution for item payloads.

Design: pressing play used to call GET /tts/{item_id}, which costs several
remote-DB round trips (and worst-case a live synthesis) before the client even
learns the audio URL (~30 s perceived latency on the Supabase dev pooler).
Instead, item payloads carry the cached Cloudinary URL directly: derive every
item's tts_cache key in Python (the exact key function the cache uses) and
resolve them all with ONE query per request — never one per item. Items with
no cached audio get null and the client falls back to the /tts route.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sauti.models import Item
from sauti.models.speech import TtsCache
from sauti.speech.cache import cache_key


def item_cache_key(item: Item) -> str:
    """The tts_cache key GET /tts/{item_id} ends up using for this item:
    RealSpeechBackend.tts calls cache.get_or_create(sentence, str(voice_id or ""))."""
    return cache_key(str(item.voice_id or ""), item.sentence)


async def audio_urls_for_items(
    db: AsyncSession, items: Sequence[Item]
) -> dict[uuid.UUID, str]:
    """item_id -> cached audio URL, resolved with a single tts_cache query."""
    keys = {item.id: item_cache_key(item) for item in items}
    if not keys:
        return {}
    rows = (
        await db.execute(
            select(TtsCache.key, TtsCache.url).where(TtsCache.key.in_(set(keys.values())))
        )
    ).all()
    url_by_key = {key: url for key, url in rows}
    return {item_id: url_by_key[k] for item_id, k in keys.items() if k in url_by_key}
