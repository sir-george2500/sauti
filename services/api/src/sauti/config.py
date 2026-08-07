"""Application settings.

Reads the repo-root .env (two levels above services/api) plus process env.
Process env always wins, so tests can override without touching files.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3].parent  # services/api -> repo root
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"
    database_schema: str = "sauti"

    jwt_secret: str = ""
    jwt_issuer: str = "sauti"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30
    cookie_secure: bool = False  # True in prod (config-driven, like rent-rwanda)

    # Only trust X-Forwarded-For for rate-limit keys when a proxy we control
    # sets it (otherwise the header is client-spoofable = free limit bypass).
    trust_proxy_headers: bool = False

    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    sauti_fake_ai: bool = False

    # Real speech stack (SAUTI_FAKE_AI=0): rent-rwanda voice service (YourTTS
    # Kinyarwanda / Kokoro English) + Cloudinary as the synthesize-once cache.
    # Empty VOICE_SERVICE_URL keeps the deterministic stub backend.
    voice_service_url: str = ""
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    app_base_url: str = "http://localhost:8000"
    app_frontend_url: str = "http://localhost:3000"

    # Tests: NullPool so connections never outlive a test's event loop.
    db_null_pool: bool = False

    # Per-surface rate limits (fixed window, seconds)
    rate_limit_window_s: int = 60
    rate_limit_auth_max: int = 10
    rate_limit_conversation_max: int = 20

    # Local storage for stub speech artefacts
    audio_dir: str = str(Path(__file__).resolve().parents[2] / "var" / "audio")
    tts_dir: str = str(Path(__file__).resolve().parents[2] / "var" / "tts")

    def _url_parts(self) -> tuple[str, str, dict[str, str]]:
        """Split POSTGRES_URL into (netloc-ish base without driver, path, query dict)."""
        raw = self.postgres_url
        split = urlsplit(raw)
        query = {k: v[0] for k, v in parse_qs(split.query).items()}
        return split.netloc, split.path, query

    @property
    def ssl_required(self) -> bool:
        _, _, q = self._url_parts()
        return q.get("sslmode", "").lower() in {"require", "verify-ca", "verify-full"}

    @property
    def async_dsn(self) -> str:
        """postgresql+asyncpg:// URL with sslmode stripped (passed via connect_args)."""
        netloc, path, query = self._url_parts()
        query.pop("sslmode", None)
        return urlunsplit(("postgresql+asyncpg", netloc, path, urlencode(query), ""))

    @property
    def sync_dsn(self) -> str:
        """postgresql+psycopg:// URL for Alembic (psycopg understands sslmode natively)."""
        netloc, path, query = self._url_parts()
        return urlunsplit(("postgresql+psycopg", netloc, path, urlencode(query), ""))

    def validate_runtime(self) -> None:
        if len(self.jwt_secret.encode()) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 bytes")
        if self.app_base_url.startswith("https://") and not self.cookie_secure:
            raise RuntimeError(
                "COOKIE_SECURE must be true when APP_BASE_URL is https:// "
                "(refresh cookie would otherwise be sent over plaintext)"
            )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    return s


def reset_settings_cache() -> None:
    get_settings.cache_clear()
