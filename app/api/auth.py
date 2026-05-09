from fastapi import APIRouter, HTTPException,Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import Optional
from app.db.database import get_db
from app.models.models import User, RefreshToken, LoginLog
from app.schemas.schemas import UserRegister, UserResponse, UserLogin, TokenResponse, RefreshTokenRequest
from app.core.utils import (
    hash_password, verify_password, create_access_token,
    create_refresh_token
)
from app.core.redis_client import get_redis

router = APIRouter(prefix="/auth", tags=["认证"])

# 获取客户端IP
def get_client_ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# 记录登录日志
async def log_login(
        db: AsyncSession,
        user_id: Optional[int],
        username: str,
        ip: str,
        user_agent: str,
        success: bool
):
    log = LoginLog(
        user_id = user_id,
        username = username,
        ip = ip,
        user_agent = user_agent,
        success = success
    )
    db.add(log)
    await db.commit()

# 获取 Redis连接
r = get_redis()

# Redis 登录函数
# 获取登录失败次数
def login_failed_count(username: str) -> int:
    key = f"login_failed: {username}"
    count = r.get(key)
    return int(count) if count else 0

# 记录登录失败
def record_login_failed(username: str) -> int:
    key = f"login_failed: {username}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 900)
    return count

# 登录成功重置失败计数
def reset_login_failed(username: str):
    r.delete(f"login_failed: {username}")

# 检查账号是否被锁定
def is_account_locked(username: str) -> bool:
    return r.exists(f"account_locked: {username}") == 1

# 锁定账号
def lock_account(username: str, lockout_minutes: int = 5):
    r.setex(f"account_locked: {username}", lockout_minutes * 60, "1")
    r.delete(f"login_failed: {username}")

# 解锁账号
def unlock_account(username: str):
    r.delete(f"account_locked: {username}")

# 注册接口函数
@router.post("/register", response_model=UserResponse)
# 定义一个异步函数叫register, 接受用户注册数据
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    # 查重, 判断用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    exist_user = result.scalar_one_or_none()
    # 输入用户名已存在, 抛出异常
    if exist_user:
        raise HTTPException(
            status_code=409,
            detail="用户已存在"
        )
    # 不存在, 创建用户
    new_user = User(
        username = user_data.username,
        password_hash = hash_password(user_data.password),
        role = "user"
    )
    db.add(new_user)
    await db.commit()
    # 刷新一下
    await db.refresh(new_user)
    # 返回用户信息
    return UserResponse(
        id = new_user.id,
        username = new_user.username,
        role = new_user.role
    )

# 登录接口
@router.post("/login", response_model=TokenResponse)
async def login(request: Request, user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    username = user_data.username
    # 1.检查是否被锁定
    if is_account_locked(username):
        await log_login(db, None, username, ip, user_agent, False)
        raise HTTPException(
            status_code = 403,
            detail = "用户已锁定，请5分钟后重试..."
        )

    # 2.查询用户
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()

    # 3.验证密码
    password_valid = user and verify_password(user_data.password, user.password_hash)
    if not user or not password_valid:
        failed_count = record_login_failed(username)
        await log_login(db, user.id if user else None, username, ip, user_agent, False)
        if failed_count >= 5:
            lock_account(username)
            raise HTTPException(
                status_code = 403,
                detail = "用户已锁定，请5分钟后重试..."
            )
        remaining = 5 - failed_count
        raise HTTPException(
            status_code=401,
            detail=f"用户名或密码错误，还剩 {remaining} 次尝试"
        )

    # 4.登录成功
    reset_login_failed(username)
    unlock_account(username)


    # 5.生成 token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id, db)
    # 6.记录登录日志
    await log_login(db, user.id, user.username, ip, user_agent, True)
    return TokenResponse(
        access_token = access_token,
        refresh_token = refresh_token,
        token_type = "bearer"
    )

# 刷新 token
@router.post("/refresh", response_model=TokenResponse)
async def refresh(req:  RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.token == req.refresh_token,
        RefreshToken.revoked == False,
        RefreshToken.expire_at > datetime.now(timezone.utc)
    ))
    token_record = result.scalar_one_or_none()
    if not token_record:
        raise HTTPException(
            status_code=401,
            detail="无效或已过期的 refresh_token"
        )
    new_access_token = create_access_token(data={"sub": str(token_record.user_id)})
    return TokenResponse(
        access_token = new_access_token,
        refresh_token = req.refresh_token,
        token_type = "bearer"
    )

# 退出登录
@router.post("/logout")
async def logout(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == req.refresh_token))
    token_record = result.scalar_one_or_none()
    if token_record:
        token_record.revoked = True
        await db.commit()

    return {"msg": "退出成功"}
