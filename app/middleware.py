from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings

RequestHandler = Callable[[Request], object]


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        response = await call_next(request)
        if isinstance(response, Response):
            response.headers["x-request-id"] = request_id
            return response
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid response")


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        if not self._settings.api_keys or request.url.path in {"/health", "/"}:
            response = await call_next(request)
            if isinstance(response, Response):
                return response
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid response")

        auth = request.headers.get("authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        api_key = request.headers.get("x-api-key", "")
        if token not in self._settings.api_keys and api_key not in self._settings.api_keys:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        response = await call_next(request)
        if isinstance(response, Response):
            return response
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid response")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)
        self._limit = settings.rate_limit_per_minute
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        if self._limit <= 0:
            response = await call_next(request)
            if isinstance(response, Response):
                return response
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid response")

        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self._limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        window.append(now)
        response = await call_next(request)
        if isinstance(response, Response):
            response.headers["x-ratelimit-limit"] = str(self._limit)
            response.headers["x-ratelimit-remaining"] = str(max(self._limit - len(window), 0))
            return response
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid response")
