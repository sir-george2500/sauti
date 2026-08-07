"""CloudinaryAudioCache — synthesize a phrase once, fetch it from Cloudinary forever.

Key design: the cache key IS the Cloudinary public id —
    key = sha256(f"{voice}|{text}").hexdigest()[:32]
    public_id = f"sauti/tts/{key}"
so existence can be checked with a plain HEAD on the deterministic delivery URL,
no Admin API needed. Lookup order (cheapest first):

  1. in-process dict         (~0 ms; the DB is a remote pooler, ~1 s away)
  2. tts_cache DB row        (survives restarts, shared across workers)
  3. HEAD deterministic URL  (covers rows lost to a wiped DB)
  4. synth_fn -> local WAV -> signed Cloudinary upload -> secure_url

Degradation: if Cloudinary is unreachable the freshly synthesized WAV is kept in
`local_dir` (served by GET /api/v1/speech/audio/{ref}) and a local URL is
returned — remembered in memory only, so Cloudinary is retried after restart.
"""
from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sauti.models.speech import TtsCache

SynthFn = Callable[[], Awaitable[bytes]]

UPLOAD_TIMEOUT_S = 30.0
HEAD_TIMEOUT_S = 10.0


def cache_key(voice: str, text: str) -> str:
    return hashlib.sha256(f"{voice}|{text}".encode()).hexdigest()[:32]


class CloudinaryAudioCache:
    def __init__(
        self,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        sessionmaker: async_sessionmaker[AsyncSession] | None,
        local_dir: str,
        local_base_url: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._cloud = cloud_name
        self._api_key = api_key
        self._api_secret = api_secret
        self._sessionmaker = sessionmaker
        self._local_dir = Path(local_dir)
        self._local_dir.mkdir(parents=True, exist_ok=True)
        self._local_base_url = local_base_url.rstrip("/")
        self._transport = transport
        self._mem: dict[str, str] = {}
        # Observability for the prerender script / report.
        self.stats = {"mem": 0, "db": 0, "head": 0, "synth": 0, "local_fallback": 0}

    # -- public API ----------------------------------------------------------
    def local_ref(self, key: str) -> str:
        return f"tts-{key}.wav"

    async def preload(self) -> int:
        """Bulk-load every known key -> url into the in-process cache (one query
        instead of one per phrase — the DB is a remote pooler). Best-effort."""
        if self._sessionmaker is None:
            return 0
        try:
            async with self._sessionmaker() as db:
                rows = list(await db.scalars(select(TtsCache)))
        except Exception:  # noqa: BLE001
            return 0
        for row in rows:
            self._mem.setdefault(row.key, row.url)
        return len(rows)

    async def get_or_create(self, key_text: str, voice: str, synth_fn: SynthFn) -> str:
        key = cache_key(voice, key_text)

        url = self._mem.get(key)
        if url:
            self.stats["mem"] += 1
            return url

        url = await self._db_get(key)
        if url:
            self.stats["db"] += 1
            self._mem[key] = url
            return url

        url = await self._head_existing(key)
        if url:
            self.stats["head"] += 1
            await self._db_put(key, voice, url)
            self._mem[key] = url
            return url

        # Miss everywhere: synthesize (the only expensive path), keep a local
        # copy for graceful degradation, then try to make it permanent.
        wav = await synth_fn()
        self.stats["synth"] += 1
        local_path = self._local_dir / self.local_ref(key)
        tmp = local_path.with_suffix(".tmp")
        tmp.write_bytes(wav)
        tmp.rename(local_path)

        url = await self._upload(key, wav)
        if url:
            await self._db_put(key, voice, url)
            self._mem[key] = url
            return url

        # Cloudinary unreachable — serve the local WAV; memory-only so the
        # upload is retried after a restart.
        self.stats["local_fallback"] += 1
        url = f"{self._local_base_url}/api/v1/speech/audio/{self.local_ref(key)}"
        self._mem[key] = url
        return url

    # -- cloudinary ----------------------------------------------------------
    def _delivery_url(self, key: str) -> str:
        # Audio is resource_type "video" on Cloudinary.
        return f"https://res.cloudinary.com/{self._cloud}/video/upload/sauti/tts/{key}.wav"

    def _client(self, timeout: float) -> httpx.AsyncClient:
        if self._transport is not None:
            return httpx.AsyncClient(transport=self._transport, timeout=timeout)
        return httpx.AsyncClient(timeout=timeout)

    async def _head_existing(self, key: str) -> str | None:
        url = self._delivery_url(key)
        try:
            async with self._client(HEAD_TIMEOUT_S) as client:
                resp = await client.head(url)
            return url if resp.status_code == 200 else None
        except httpx.HTTPError:
            return None

    async def _upload(self, key: str, wav: bytes) -> str | None:
        """Signed direct upload via httpx — no cloudinary SDK dependency."""
        public_id = f"sauti/tts/{key}"
        timestamp = str(int(time.time()))
        to_sign = f"overwrite=true&public_id={public_id}&timestamp={timestamp}"
        signature = hashlib.sha1((to_sign + self._api_secret).encode()).hexdigest()
        try:
            async with self._client(UPLOAD_TIMEOUT_S) as client:
                resp = await client.post(
                    f"https://api.cloudinary.com/v1_1/{self._cloud}/video/upload",
                    data={
                        "api_key": self._api_key,
                        "timestamp": timestamp,
                        "public_id": public_id,
                        "overwrite": "true",
                        "signature": signature,
                    },
                    files={"file": (f"{key}.wav", wav, "audio/wav")},
                )
            if resp.status_code != 200:
                return None
            url = resp.json().get("secure_url")
            return url or None
        except (httpx.HTTPError, ValueError):
            return None

    # -- local DB index (fast lookup seam; monkeypatchable in unit tests) ----
    async def _db_get(self, key: str) -> str | None:
        if self._sessionmaker is None:
            return None
        try:
            async with self._sessionmaker() as db:
                row = await db.scalar(select(TtsCache).where(TtsCache.key == key))
                return row.url if row else None
        except Exception:  # noqa: BLE001 — cache index down must never break TTS
            return None

    async def _db_put(self, key: str, voice: str, url: str) -> None:
        if self._sessionmaker is None:
            return
        try:
            async with self._sessionmaker() as db:
                db.add(TtsCache(key=key, voice=voice, url=url))
                await db.commit()
        except IntegrityError:
            pass  # concurrent writer won the race — same deterministic URL
        except Exception:  # noqa: BLE001
            pass
