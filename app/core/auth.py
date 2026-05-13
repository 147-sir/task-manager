from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.models.models import LoginLog
from app.core.redis_client import get_redis

def get_client_ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def log_login(
        db: AsyncSession,
        user_id: Optional[int],
        username: str,
        ip: str,
        user_agent: str,
        success: bool
):
    if user_id is None:
        return
    log = LoginLog(
        user_id = user_id,
        username = username,
        ip = ip,
        user_agent = user_agent,
        success = success
    )
    db.add(log)
    await db.commit()

r = get_redis()

def login_failed_count(username: str) -> int:
    key = f"login_failed:{username}"
    count = r.get(key)
    return int(count) if count else 0

def record_login_failed(username: str) -> int:
    key = f"login_failed:{username}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 900)
    return count

def reset_login_failed(username: str):
    r.delete(f"login_failed:{username}")

def is_account_locked(username: str) -> bool:
    return r.exists(f"account_locked:{username}") == 1

def locked_account(username: str, lockout_minutes: int = 5):
    r.setex(f"account_locked:{username}", lockout_minutes * 60, "1")

def unlock_account(username: str):
    r.delete(f"account_locked:{username}")
