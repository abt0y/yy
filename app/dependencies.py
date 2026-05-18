from __future__ import annotations

from typing import cast

from fastapi import Request

from app.config import Settings
from core.account_pool import AccountPool
from core.gemini_client import GeminiClientManager
from core.history import FileStore


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_account_pool(request: Request) -> AccountPool:
    return cast(AccountPool, request.app.state.account_pool)


def get_gemini_manager(request: Request) -> GeminiClientManager:
    return cast(GeminiClientManager, request.app.state.gemini_manager)


def get_file_store(request: Request) -> FileStore:
    return cast(FileStore, request.app.state.file_store)
