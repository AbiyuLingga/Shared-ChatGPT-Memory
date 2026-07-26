from __future__ import annotations

import secrets
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.auth import Authenticator
from app.config import Settings, get_settings
from app.mem0_client import Mem0Client
from app.rate_limit import RateLimiter
from app.routes.memories import router as memories_router
from app.routes.public import router as public_router
from app.services.change_service import ChangeService
from app.services.memory_service import MemoryService


def create_app(
    settings: Settings | None = None,
    *,
    mem0_client: Mem0Client | None = None,
    authenticator: Authenticator | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    client = mem0_client or Mem0Client(
        settings.mem0_api_key.get_secret_value(),
        settings.memory_vault_id,
        base_url=settings.mem0_base_url,
        poll_timeout=settings.mem0_add_wait_seconds,
        poll_interval=settings.mem0_poll_interval_seconds,
        timeout_seconds=settings.request_timeout_seconds,
        server_metadata={"source": "custom-gpt", "schema_version": "1"},
    )
    memory_service = MemoryService(client, settings.memory_vault_id)
    change_service = ChangeService(
        memory_service, token_secret=settings.change_token_secret.get_secret_value()
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if client is not mem0_client:
            await client.__aexit__(None, None, None)

    docs_enabled = settings.environment.lower() not in {"production", "prod"}
    app = FastAPI(
        title="Shared ChatGPT Memory",
        version="1.0.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.authenticator = authenticator or Authenticator(settings=settings)
    app.state.memory_service = memory_service
    app.state.change_service = change_service
    app.state.rate_limiter = RateLimiter()

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = secrets.token_hex(8)
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store"
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Response-Time-ms"] = str(elapsed_ms)
        return response

    app.include_router(public_router)
    app.include_router(memories_router)
    return app


# Keep import side-effect free so tests and tooling can import the factory
# without requiring production secrets. Uvicorn invokes this callable with
# ``--factory`` after Railway Variables are present.
app = create_app
