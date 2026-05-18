from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from gemini_webapi import GeminiClient

from app.config import Settings
from core.account_pool import Account, AccountPool


class GeminiClientManager:
    def __init__(self, pool: AccountPool, settings: Settings) -> None:
        self._pool = pool
        self._settings = settings
        self._clients: dict[str, GeminiClient] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def generate(
        self,
        prompt: str,
        model: str,
        files: list[Path],
        temporary: bool | None,
    ) -> str:
        account = await self._pool.next_account()
        client = await self._get_client(account)
        try:
            output = await client.generate_content(
                prompt,
                files=files or None,
                model=model,
                temporary=self._temporary_mode(temporary),
            )
            return output.text
        except Exception:
            await self._pool.mark_failure(account.id)
            raise

    async def stream(
        self,
        prompt: str,
        model: str,
        files: list[Path],
        temporary: bool | None,
    ) -> AsyncIterator[str]:
        account = await self._pool.next_account()
        client = await self._get_client(account)
        try:
            async for output in client.generate_content_stream(
                prompt,
                files=files or None,
                model=model,
                temporary=self._temporary_mode(temporary),
            ):
                yield output.text
        except Exception:
            await self._pool.mark_failure(account.id)
            raise

    async def close(self) -> None:
        for client in self._clients.values():
            client.close()
        self._clients.clear()

    async def _get_client(self, account: Account) -> GeminiClient:
        lock = self._locks.setdefault(account.id, asyncio.Lock())
        async with lock:
            client = self._clients.get(account.id)
            if client is not None:
                return client
            client = GeminiClient(account.secure_1psid, account.secure_1psidts, proxy=account.proxy)
            await client.init(
                timeout=self._settings.request_timeout_seconds,
                auto_close=True,
                close_delay=self._settings.close_delay_seconds,
                auto_refresh=self._settings.auto_refresh,
            )
            self._clients[account.id] = client
            return client

    def _temporary_mode(self, temporary: bool | None) -> bool:
        if temporary is None:
            return self._settings.temporary_chat
        return temporary
