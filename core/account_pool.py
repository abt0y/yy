from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from app.config import CookieConfig, Settings

JsonMap = dict[str, object]


@dataclass(slots=True)
class Account:
    id: str
    secure_1psid: str
    secure_1psidts: str = ""
    proxy: str | None = None
    enabled: bool = True
    fail_count: int = 0


class AccountPool:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._accounts: dict[str, Account] = {}
        self._order: list[str] = []
        self._index = 0
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        self._settings.cookies_dir.mkdir(parents=True, exist_ok=True)
        for cookie in self._settings.cookies:
            await self.add_from_config(cookie)
        for path in sorted(self._settings.cookies_dir.glob("*.json")):
            cookie = self._read_cookie_file(path)
            if cookie is not None:
                await self.add(cookie)

    async def add_from_config(self, cookie: CookieConfig) -> Account:
        return await self.add(
            Account(
                id=cookie.id,
                secure_1psid=cookie.secure_1psid,
                secure_1psidts=cookie.secure_1psidts,
                proxy=cookie.proxy,
                enabled=cookie.enabled,
            )
        )

    async def add(self, account: Account) -> Account:
        async with self._lock:
            self._accounts[account.id] = account
            if account.id not in self._order:
                self._order.append(account.id)
        return account

    async def add_runtime_cookie(
        self,
        secure_1psid: str,
        secure_1psidts: str,
        proxy: str | None,
        enabled: bool,
        account_id: str | None,
    ) -> Account:
        candidate_id = account_id or f"cookie-{secrets.token_hex(4)}"
        account = Account(
            id=candidate_id,
            secure_1psid=secure_1psid,
            secure_1psidts=secure_1psidts,
            proxy=proxy,
            enabled=enabled,
        )
        await self.add(account)
        self._write_cookie_file(account)
        return account

    async def remove(self, account_id: str) -> bool:
        async with self._lock:
            existed = account_id in self._accounts
            if existed:
                del self._accounts[account_id]
            self._order = [item for item in self._order if item != account_id]
        path = self._settings.cookies_dir / f"{account_id}.json"
        if path.exists():
            path.unlink()
        return existed

    async def next_account(self) -> Account:
        async with self._lock:
            enabled = [self._accounts[item] for item in self._order if self._accounts[item].enabled]
            if not enabled:
                raise RuntimeError("No enabled Gemini cookie accounts configured")
            account = enabled[self._index % len(enabled)]
            self._index += 1
            return account

    async def mark_failure(self, account_id: str) -> None:
        async with self._lock:
            account = self._accounts.get(account_id)
            if account is not None:
                account.fail_count += 1

    def list_accounts(self) -> list[Account]:
        return list(self._accounts.values())

    def enabled_count(self) -> int:
        return len([account for account in self._accounts.values() if account.enabled])

    def _read_cookie_file(self, path: Path) -> Account | None:
        with path.open("r", encoding="utf-8") as handle:
            raw: object = json.load(handle)
        if not isinstance(raw, dict):
            return None
        data = cast(JsonMap, raw)
        secure_1psid = data.get("secure_1psid") or data.get("__Secure-1PSID")
        if not isinstance(secure_1psid, str) or not secure_1psid:
            return None
        secure_1psidts = data.get("secure_1psidts") or data.get("__Secure-1PSIDTS")
        proxy = data.get("proxy")
        enabled = data.get("enabled")
        cookie_id = data.get("id")
        return Account(
            id=cookie_id if isinstance(cookie_id, str) and cookie_id else path.stem,
            secure_1psid=secure_1psid,
            secure_1psidts=secure_1psidts if isinstance(secure_1psidts, str) else "",
            proxy=proxy if isinstance(proxy, str) and proxy else None,
            enabled=enabled if isinstance(enabled, bool) else True,
        )

    def _write_cookie_file(self, account: Account) -> None:
        self._settings.cookies_dir.mkdir(parents=True, exist_ok=True)
        path = self._settings.cookies_dir / f"{account.id}.json"
        data: JsonMap = {
            "id": account.id,
            "secure_1psid": account.secure_1psid,
            "secure_1psidts": account.secure_1psidts,
            "proxy": account.proxy or "",
            "enabled": account.enabled,
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
