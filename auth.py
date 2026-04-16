from fastapi import APIRouter, HTTPException,Depends
from schemas import UserRegister, UserResponse, UserLogin, TokenResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from jose import jwt
import bcrypt

load_dotenv()

# 注册
router = APIRouter(prefix="/auth", tags=["认证"])
#1.先定加密方式: bcrypt; deprecated="auto": 自动兼容旧的、过时的加密算法。
pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")

#2.用hash方法进行加密 (函数)
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 登录
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 登录令牌(函数)
def create_access_token(data: dict) -> str:
    # 把存进去的数据复制一份
    to_encode = data.copy()
    # 设置过期时间(30分钟失效), timezone.utc表示统一时间，避免服务器、你本地、用户所在时区不一样，导致过期时间算错
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # 把过期时间放进 token 里
    to_encode.update({"exp": expire})
    # # 生成 JWT 字符串并返回
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        # 用户输入的明文密码
        plain_password.encode('utf-8'),
        # 数据库里存的加密密码
        hashed_password.encode('utf-8')
    )

# 接口函数
@router.post("/register", response_model=UserResponse)
# 定义一个异步函数叫register, 接受用户注册数据
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    # 查重, 判断用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    exist_user = result.scalar_one_or_none()
    # 输入用户名已存在, 抛出异常
    if exist_user:
        raise HTTPException(
            status_code=404,
            detail="用户已存在"
        )
    # 不存在, 创建用户
    new_user = User(
        username = user_data.username,
        password_hash = hash_password(user_data.password),
        email = user_data.email
    )
    db.add(new_user)
    await db.commit()
    # 刷新一下
    await db.refresh(new_user)
    # 返回用户信息
    return UserResponse(
        id = new_user.id,
        username = new_user.username,
        email = new_user.email
    )

# 登录接口
@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    # 查询用户
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code= 404,
            detail="用户不存在"
        )
    # 验证密码
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code= 404,
            detail="用户名或密码错误"
        )

    # 生成 token
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, token_type="bearer")
