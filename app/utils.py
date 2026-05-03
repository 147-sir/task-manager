from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt
from jose import jwt
from typing import Optional
from passlib.context import CryptContext
import secrets
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from app.models import RefreshToken

load_dotenv()

# 环境配置
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 加密处理
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
# 验证密码
def verify_password(plain_password: str, hashed_password:str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

# 处理Token
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)
async def create_refresh_token(user_id: int, db: AsyncSession) -> str:
    token_str = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = RefreshToken(
        user_id = user_id,
        token = token_str,
        expire_at = expires_at,
        revoked = False
    )
    db.add(refresh_token)
    await db.commit()
    return token_str
def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None

# 账号锁定处理
_failed_login_cache = {}
def record_failed_login(username: str) -> int:
    count = _failed_login_cache.get(username, 0) + 1
    _failed_login_cache[username] = count
    return count
def clear_failed_logins(username: str) ->None:
    if username in _failed_login_cache:
        del _failed_login_cache[username]
def get_failed_count(username: str) -> int:
    return _failed_login_cache.get(username, 0)

