"""Sauti API — FastAPI application factory.

Run from services/api:  uv run uvicorn sauti.main:app --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sauti.config import Settings, get_settings
from sauti.db import build_engine, build_sessionmaker
from sauti.errors import install_error_handlers
from sauti.llm.fake import FakeLlmClient
from sauti.llm.openai_client import OpenAiLlmClient
from sauti.rate_limit import RateLimiter
from sauti.routers import (
    auth,
    conversation_ws,
    courses,
    health,
    learning,
    me,
    placement,
    scenarios,
    speech,
)
from sauti.services.mail import ConsoleMailer, SmtpMailer
from sauti.speech.cache import CloudinaryAudioCache
from sauti.speech.gateway import StubSpeechBackend
from sauti.speech.real import RealSpeechBackend

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.validate_runtime()  # e.g. JWT secret >= 32 bytes, enforced at startup
        yield
        aclose = getattr(app.state.llm_client, "aclose", None)
        if aclose is not None:
            await aclose()
        await app.state.engine.dispose()

    app = FastAPI(title="Sauti API", version="0.1.0", lifespan=lifespan)

    app.state.settings = settings
    app.state.engine = build_engine(settings)
    app.state.sessionmaker = build_sessionmaker(app.state.engine)
    app.state.rate_limiter = RateLimiter(window_s=settings.rate_limit_window_s)
    # SpeechGateway seam: real YourTTS (through the Cloudinary synthesize-once
    # cache) when configured; deterministic stub for SAUTI_FAKE_AI=1 / e2e.
    if settings.sauti_fake_ai or not settings.voice_service_url:
        app.state.speech_gateway = StubSpeechBackend(settings.audio_dir, settings.tts_dir)
    else:
        tts_cache = CloudinaryAudioCache(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            sessionmaker=app.state.sessionmaker,
            local_dir=settings.tts_dir,
            local_base_url=settings.app_base_url,
        )
        app.state.speech_gateway = RealSpeechBackend(
            settings.audio_dir,
            settings.tts_dir,
            voice_service_url=settings.voice_service_url,
            cache=tts_cache,
        )

    # Mailer seam: real SMTP only when fully configured and not in fake-AI
    # mode; otherwise the capturing ConsoleMailer (dev, tests, e2e).
    if settings.sauti_fake_ai or not (
        settings.smtp_host and settings.smtp_username and settings.smtp_password
    ):
        app.state.mailer = ConsoleMailer()
    else:
        app.state.mailer = SmtpMailer(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            mail_from=settings.app_mail_from,
            starttls=settings.smtp_starttls,
        )

    # LlmClient seam: SAUTI_FAKE_AI=1 forces the scripted fake (e2e runs use this).
    if settings.sauti_fake_ai:
        app.state.llm_client = FakeLlmClient()
    else:
        app.state.llm_client = OpenAiLlmClient(
            api_key=settings.openai_api_key, model=settings.openai_chat_model
        )

    # CORS: frontend origin only, with credentials (refresh cookie) and the
    # audio PUT to the upload URL. No DELETE routes exist — don't allow it.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.app_frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        # nosniff matters most on /speech/audio/{ref}: user-uploaded bytes are
        # served back and must never be content-sniffed into HTML.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith(f"{API_PREFIX}/auth"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    install_error_handlers(app)

    for r in (
        health.router,
        auth.router,
        me.router,
        courses.router,
        learning.router,
        placement.router,
        speech.router,
        scenarios.router,
        conversation_ws.router,
    ):
        app.include_router(r, prefix=API_PREFIX)

    # Convenience alias outside the versioned prefix.
    app.include_router(health.router)

    # Test-only surface (captured-mail readback for e2e) — fake-AI mode only.
    if settings.sauti_fake_ai:
        from sauti.routers import testonly

        app.include_router(testonly.router)

    return app


app = create_app()
