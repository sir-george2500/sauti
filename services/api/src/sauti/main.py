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
from sauti.speech.gateway import StubSpeechBackend

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.validate_runtime()  # e.g. JWT secret >= 32 bytes, enforced at startup
        yield
        await app.state.engine.dispose()

    app = FastAPI(title="Sauti API", version="0.1.0", lifespan=lifespan)

    app.state.settings = settings
    app.state.engine = build_engine(settings)
    app.state.sessionmaker = build_sessionmaker(app.state.engine)
    app.state.rate_limiter = RateLimiter(window_s=settings.rate_limit_window_s)
    app.state.speech_gateway = StubSpeechBackend(settings.audio_dir, settings.tts_dir)

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

    return app


app = create_app()
