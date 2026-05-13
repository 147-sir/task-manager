from fastapi import Request
from fastapi.responses import JSONResponse
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
import time

request_records = defaultdict(list)

RATE_LIMITS = {
    "/auth/login": (5, 60),
    "/auth/register": (30, 60),
    "/tasks": (100, 60),
    "/admin": (200, 60)
}

DEFAULT_LIMIT = (100, 60)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        path = request.url.path
        limit = DEFAULT_LIMIT
        for k, v in RATE_LIMITS.items():
            if k in path:
                limit = v
                break
        max_requests, window_seconds = limit
        key = f"{client_ip}:{path}"

        now = time.time()

        request_records[key] = [
            req_time for req_time in request_records[key]
            if now - req_time < window_seconds
        ]
        if len(request_records[key]) >= max_requests:
            return JSONResponse(
                status_code=429,
                content=f"请求太频繁，请{window_seconds}秒后再试"
            )
        request_records[key].append(now)

        response = await call_next(request)
        return response

