from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import yaml

ConfigMap = dict[str, object]


@dataclass(slots=True)
class CookieConfig:
    id: str
    secure_1psid: str
    secure_1psidts: str = ""
    proxy: str | None = None
    enabled: bool = True


@dataclass(slots=True)
class Settings:
    app_name: str = "Gemini Web API"
    host: str = "0.0.0.0"
    port: int = 8000
    config_path: Path = Path("config.yaml")
    cookies_dir: Path = Path("cookies")
    upload_dir: Path = Path("uploads")
    api_keys: list[str] = field(default_factory=list)
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    rate_limit_per_minute: int = 120
    request_timeout_seconds: float = 60.0
    close_delay_seconds: float = 300.0
    auto_refresh: bool = True
    default_model: str = "gemini-2.5-pro"
    models: list[str] = field(
        default_factory=lambda: [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ]
    )
    temporary_chat: bool = True
    cookies: list[CookieConfig] = field(default_factory=list)


def _as_map(value: object) -> ConfigMap:
    if isinstance(value, dict):
        return cast(ConfigMap, value)
    return {}


def _as_list_of_strings(value: object, fallback: list[str]) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return fallback


def _as_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return fallback


def _as_int(value: object, fallback: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return fallback


def _as_float(value: object, fallback: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return fallback
    return fallback


def _load_yaml(path: Path) -> ConfigMap:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded: object = yaml.safe_load(handle)
    return _as_map(loaded)


def _load_cookie_configs(raw_cookies: object) -> list[CookieConfig]:
    if not isinstance(raw_cookies, list):
        return []

    cookies: list[CookieConfig] = []
    for index, item in enumerate(raw_cookies):
        cookie = _as_map(item)
        secure_1psid = cookie.get("secure_1psid")
        if not isinstance(secure_1psid, str) or not secure_1psid:
            continue
        cookie_id = cookie.get("id")
        secure_1psidts = cookie.get("secure_1psidts")
        proxy = cookie.get("proxy")
        enabled = cookie.get("enabled")
        cookies.append(
            CookieConfig(
                id=cookie_id if isinstance(cookie_id, str) and cookie_id else f"config-{index + 1}",
                secure_1psid=secure_1psid,
                secure_1psidts=secure_1psidts if isinstance(secure_1psidts, str) else "",
                proxy=proxy if isinstance(proxy, str) and proxy else None,
                enabled=_as_bool(enabled, True),
            )
        )
    return cookies


def load_settings() -> Settings:
    config_path = Path(os.getenv("GWA_CONFIG", "config.yaml"))
    config = _load_yaml(config_path)

    app = _as_map(config.get("app"))
    gemini = _as_map(config.get("gemini"))
    security = _as_map(config.get("security"))
    server = _as_map(config.get("server"))

    default_models = Settings().models
    settings = Settings(
        app_name=str(app.get("name") or os.getenv("GWA_APP_NAME", "Gemini Web API")),
        host=str(server.get("host") or os.getenv("HOST", "0.0.0.0")),
        port=_as_int(server.get("port") or os.getenv("PORT"), 8000),
        config_path=config_path,
        cookies_dir=Path(str(gemini.get("cookies_dir") or os.getenv("GWA_COOKIES_DIR", "cookies"))),
        upload_dir=Path(str(gemini.get("upload_dir") or os.getenv("GWA_UPLOAD_DIR", "uploads"))),
        api_keys=_as_list_of_strings(security.get("api_keys") or os.getenv("GWA_API_KEYS", ""), []),
        cors_origins=_as_list_of_strings(security.get("cors_origins") or os.getenv("GWA_CORS_ORIGINS", "*"), ["*"]),
        rate_limit_per_minute=_as_int(
            security.get("rate_limit_per_minute") or os.getenv("GWA_RATE_LIMIT_PER_MINUTE"),
            120,
        ),
        request_timeout_seconds=_as_float(
            gemini.get("request_timeout_seconds") or os.getenv("GWA_REQUEST_TIMEOUT_SECONDS"),
            60.0,
        ),
        close_delay_seconds=_as_float(
            gemini.get("close_delay_seconds") or os.getenv("GWA_CLOSE_DELAY_SECONDS"),
            300.0,
        ),
        auto_refresh=_as_bool(gemini.get("auto_refresh") or os.getenv("GWA_AUTO_REFRESH"), True),
        default_model=str(gemini.get("default_model") or os.getenv("GWA_DEFAULT_MODEL", "gemini-2.5-pro")),
        models=_as_list_of_strings(gemini.get("models") or os.getenv("GWA_MODELS", ""), default_models),
        temporary_chat=_as_bool(gemini.get("temporary_chat") or os.getenv("GWA_TEMPORARY_CHAT"), True),
        cookies=_load_cookie_configs(gemini.get("cookies")),
    )
    return settings
