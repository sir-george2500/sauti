"""Pre-render item audio through the synthesize-once cache.

    uv run python -m sauti.speech.prerender [COURSE_CODE=KIN]

Walks every seeded item of the course and runs it through the real speech
backend (voice service + Cloudinary cache). Already-cached phrases are
skipped by the cache itself, so re-running is cheap and idempotent.
"""
from __future__ import annotations

import asyncio
import functools
import sys
import time

print = functools.partial(print, flush=True)  # progress must show through a pipe

from sqlalchemy import select

from sauti.config import get_settings
from sauti.db import build_engine, build_sessionmaker
from sauti.models import Course, Item, Lesson, Level, Unit
from sauti.speech.cache import CloudinaryAudioCache
from sauti.speech.real import RealSpeechBackend


async def main(course_code: str = "KIN") -> None:
    settings = get_settings()
    if not settings.voice_service_url:
        raise SystemExit("VOICE_SERVICE_URL is not set — nothing to prerender with.")

    engine = build_engine(settings)
    maker = build_sessionmaker(engine)
    cache = CloudinaryAudioCache(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        sessionmaker=maker,
        local_dir=settings.tts_dir,
        local_base_url=settings.app_base_url,
    )
    backend = RealSpeechBackend(
        settings.audio_dir,
        settings.tts_dir,
        voice_service_url=settings.voice_service_url,
        cache=cache,
    )

    async with maker() as db:
        items = list(
            await db.scalars(
                select(Item)
                .join(Lesson, Lesson.id == Item.lesson_id)
                .join(Unit, Unit.id == Lesson.unit_id)
                .join(Level, Level.id == Unit.level_id)
                .join(Course, Course.id == Level.course_id)
                .where(Course.code == course_code)
                .order_by(Level.ord, Unit.ord, Lesson.ord, Item.created_at)
            )
        )
    await engine.dispose()  # items are loaded; synthesis needs no ORM session

    print(f"{len(items)} {course_code} items to render")
    t_start = time.monotonic()
    failures = 0
    for i, item in enumerate(items, 1):
        t0 = time.monotonic()
        try:
            url = await backend.tts(item.sentence, voice=str(item.voice_id or ""))
        except Exception as exc:  # keep walking — one bad sentence must not stop the run
            failures += 1
            print(f"[{i}/{len(items)}] FAILED {type(exc).__name__}: {item.sentence[:50]}")
            continue
        took = time.monotonic() - t0
        print(f"[{i}/{len(items)}] {took:5.2f}s  {item.sentence[:44]:<44} -> {url[:72]}")

    total = time.monotonic() - t_start
    print(
        f"done in {total:.0f}s — cache stats: {cache.stats} — failures: {failures}"
    )
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "KIN"))
