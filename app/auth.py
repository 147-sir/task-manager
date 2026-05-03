from fastapi import APIRouter, HTTPException,Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Optional
from .database import get_db
from .models import User, RefreshToken, LoginLog
from .schemas import UserRegister, UserResponse, UserLogin, TokenResponse, RefreshTokenRequest
from .utils import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, record_failed_login,
    clear_failed_logins, get_failed_count
)

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
    fail_count = get_failed_count(user_data.username)
    # 查询用户
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()
    if user and user.is_locked and user.lock_until:
        if user.lock_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            await log_login(db, user.id, user.username, ip, user_agent, False)
            raise HTTPException(
                status_code=403,
                detail=f"用户已锁定至{user.lock_until}"
            )
        else:
            user.is_locked = False
            user.lock_until = None
            await db.commit()
    password_valid = user and verify_password(user_data.password, user.password_hash)
    if not user or not password_valid:
        new_count = record_failed_login(user_data.username)
        await log_login(db, user.id if user else None, user_data.username, ip, user_agent, False)
        if user and new_count >= 5:
            user.is_locked = True
            user.lock_until = datetime.now(timezone.utc) + timedelta(seconds=15)
            await db.commit()
            raise HTTPException(
                status_code=403,
                detail="密码错误次数过多，请15秒后重试..."
            )
        remaining = 5 - new_count
        raise  HTTPException(
            status_code=401,
            detail=f"用户名或密码错误，还剩 {remaining} 次尝试"
        )
    clear_failed_logins(user_data.username)
    # 生成 token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id, db)
    # 记录登录日志
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
