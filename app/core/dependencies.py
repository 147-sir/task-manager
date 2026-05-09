from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User
from app.db.database import get_db
from .utils import decode_token
from app.core.redis_client import get_redis

security = HTTPBearer()

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> User:
    # 从请求头中获取 token 字符串
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token",
        )

    result = await db.execute(select(User).where(User.id == int(user_id_str)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user
async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """需要管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

# 获取用户权限
async def get_current_permissions(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
) -> set:
    # 1.连接 Redis
    r = get_redis()
    cache_key = f"permissions:user:{current_user.id}"

    # 2.从缓存中获取数据
    cached = r.get(cache_key)
    if cached:
        print(f"权限缓存命中: user_id={current_user.id}")
        return eval(cached)

    # 3.缓存没有, 查数据库
    print(f"权限缓存未命中, 查询数据库: user_id={current_user.id}")
    permissions_map = {
        "admin": {"user:read", "user:write", "task:read", "task:write", "admin:all"},
        "user": {"task:read", "task:write"}
    }
    perms = permissions_map.get(current_user.role, set())

    # 4.写入缓存, 5分钟过期
    r.setex(cache_key, 300, str(perms))
    return perms
