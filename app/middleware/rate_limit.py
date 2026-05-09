from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
import time

# 存储请求记录
request_records = defaultdict(list)

# 限流规则配置
RATE_LIMITS = {
    # 格式: "路径关键字": (限制次数, 时间窗口秒数)
    "/auth/login": (5, 60),      # 登录接口: 限制5次/分钟
    "/auth/register": (3, 60),   # 注册接口: 限制3次/分钟
    "/tasks": (10, 60),         # 任务接口: 限制10次/分钟
    "/admin": (20, 60)         # 管理接口: 限制20次/分钟
}

# 默认限流 (其他所有接口)
DEFAULT_LIMIT = (100, 60)

class RateLimitMiddleware(BaseHTTPMiddleware):
    # 获取客户端IP
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host

        # 获取请求路径
        path = request.url.path

        # 匹配限流规则
        limit = DEFAULT_LIMIT
        for k, v in RATE_LIMITS.items():
            if k in path:
                limit = v
                break
        max_requests, window_seconds = limit
        # 生成唯一标识: IP + 路径
        key = f"{client_ip}:{path}"

        # 获取当前时间
        now = time.time()

        # 清理过期的记录(超过时间窗口的)
        request_records[key] = [
            req_time for req_time in request_records[key]
            if now - req_time < window_seconds
        ]

        # 检查是否超过限制
        if len(request_records[key]) >= max_requests:
            return JSONResponse(
                status_code=429,
                content=f"请求太频繁，请{window_seconds}秒后再试"
            )

        # 记录本次请求
        request_records[key].append(now)

        # 继续处理请求
        response = await call_next(request)
        return response




