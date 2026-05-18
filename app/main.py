from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import Settings, load_settings
from app.middleware import ApiKeyMiddleware, RateLimitMiddleware, RequestIdMiddleware
from core.account_pool import AccountPool
from core.gemini_client import GeminiClientManager
from core.history import FileStore
from models.schemas import HealthResponse
from routers import admin, claude, gemini, openai


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    pool = AccountPool(settings)
    await pool.load()
    manager = GeminiClientManager(pool, settings)
    app.state.settings = settings
    app.state.account_pool = pool
    app.state.gemini_manager = manager
    app.state.file_store = FileStore(settings.upload_dir)
    try:
        yield
    finally:
        await manager.close()


def create_app() -> FastAPI:
    settings = load_settings()
    api = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api.add_middleware(RequestIdMiddleware)
    api.add_middleware(RateLimitMiddleware, settings=settings)
    api.add_middleware(ApiKeyMiddleware, settings=settings)
    api.include_router(openai.router)
    api.include_router(claude.router)
    api.include_router(gemini.router)
    api.include_router(admin.router)
    api.mount("/admin-ui", StaticFiles(directory="admin", html=True), name="admin-ui")
    return api


app = create_app()


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "gemini-web-api", "status": "ok"}


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    pool = request.app.state.account_pool
    return HealthResponse(accounts=len(pool.list_accounts()), enabled_accounts=pool.enabled_count())
