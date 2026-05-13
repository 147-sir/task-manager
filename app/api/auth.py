from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.db.database import get_db
from app.models.models import User, RefreshToken
from app.schemas.schemas import UserRegister, UserResponse, UserLogin, TokenResponse, RefreshTokenRequest
from app.core.utils import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.auth import (
    get_client_ip, is_account_locked, log_login, record_login_failed,
    locked_account, reset_login_failed, unlock_account
)

router = APIRouter(prefix="/auth", tags=["认证"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()
    if user:
        raise HTTPException(
            status_code=409,
            detail="用户已存在"
        )
    new_user = User(
        username = user_data.username,
        password_hash = hash_password(user_data.password),
        role = "user"
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserResponse(
        id = new_user.id,
        username = new_user.username,
        role = new_user.role
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    ip: str = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    username = user_data.username
    if is_account_locked(username):
        await log_login(db, None, username, ip, user_agent, False)
        raise HTTPException(
            status_code=403,
            detail="用户已锁定，请5分钟后重试..."
        )
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    password_valid = False
    if user:
        password_valid = verify_password(user_data.password, user.password_hash)
    if not user or not password_valid:
        failed_account  = record_login_failed(username)
        await log_login(db, user.id if user else None, username, ip, user_agent, False)
        if failed_account >= 5:
            locked_account(username)
            raise HTTPException(
                status_code=403,
                detail="用户已锁定，请5分钟后重试..."
            )
        remaining = 5 - failed_account
        raise HTTPException(
            status_code=401,
            detail=f"用户名或密码错误，还剩 {remaining} 次尝试"
        )
    reset_login_failed(username)
    unlock_account(username)

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id, db)
    await log_login(db, user.id, username, ip, user_agent, True)
    return TokenResponse(
        access_token = access_token,
        refresh_token = refresh_token,
        token_type = "bearer"
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.token == req.refresh_token,
        RefreshToken.revoked ==False,
        RefreshToken.expire_at > datetime.now(timezone.utc)
    ))
    token_record = result.scalar_one_or_none()
    if not token_record:
        raise HTTPException(
            status_code = 401,
            detail = f"无效的 refresh_token"
        )
    new_access_token = create_access_token(data={"sub": str(token_record.user_id)})
    return TokenResponse(
        access_token = new_access_token,
        refresh_token = req.refresh_token,
        token_type = "bearer"
    )

@router.post("/logout")
async def logout(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == req.refresh_token))
    token_record = result.scalar_one_or_none()
    if token_record:
        token_record.revoked = True
        await db.commit()
    return {"msg": "退出成功"}
