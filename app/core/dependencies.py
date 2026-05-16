from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.models import User
from .utils import decode_token
from .redis_client import get_redis

security = HTTPBearer()

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    r = get_redis()
    if r.get(f"blacklist:{token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token已失效,请重新登录",
            headers = {"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "无效的token",
            headers = {"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "无效的token"
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "用户不存在"
        )
    return user

async def require_admin(
        current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "需要管理员权限"
        )
    return current_user

async def get_current_permissions(
        current_user: User = Depends(get_current_user)
) -> set:
    # 1.连接 Redis
    r = get_redis()
    cache_key = f"permissions:user:{current_user.id}"

    # 2.从缓存中获取数据
    cached = r.get(cache_key)
    if cached:
        print(f"缓存命中: user_id={current_user.id}")

    print(f"权限缓存未命中, 查询数据库: user_id: {current_user.id}")
    permissions_map = {
        "admin": {"user:read", "user:write", "task:read", "task:write", "admin:all"},
        "user": {"task:read", "task:write"}
    }
    perms = permissions_map.get(current_user.role, set())
    r.setex(cache_key, 300, str(perms))
    return perms
