from __future__ import annotations

import hashlib
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed fixed-window limiter with a bounded process-local fallback."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._local: defaultdict[tuple[str, int], int] = defaultdict(int)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in {"/api/v1/health/live", "/api/v1/health/ready", "/api/v1/metrics"}:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        identity = authorization or (request.client.host if request.client else "unknown")
        identity_hash = hashlib.sha256(identity.encode()).hexdigest()[:24]
        window = int(time.time() // 60)
        count = await self._increment(identity_hash, window)
        if count > settings.rate_limit_per_minute:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Request rate limit exceeded."}},
                headers={"retry-after": "60"},
            )
        response = await call_next(request)
        response.headers["x-ratelimit-limit"] = str(settings.rate_limit_per_minute)
        response.headers["x-ratelimit-remaining"] = str(max(0, settings.rate_limit_per_minute - count))
        return response

    async def _increment(self, identity_hash: str, window: int) -> int:
        if settings.environment == "production":
            try:
                from redis.asyncio import Redis

                client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)
                key = f"vernis:rate:{identity_hash}:{window}"
                count = await client.incr(key)
                if count == 1:
                    await client.expire(key, 90)
                await client.aclose()
                return int(count)
            except Exception:
                # Availability fallback remains bounded per process. Operators
                # can alert on Redis health via readiness/central monitoring.
                pass
        key = (identity_hash, window)
        self._local[key] += 1
        if len(self._local) > 20_000:
            self._local = defaultdict(int, {item: value for item, value in self._local.items() if item[1] >= window - 1})
        return self._local[key]
