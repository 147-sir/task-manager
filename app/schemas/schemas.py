from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: int
    username: str
    role: str = 'user'

# 定义登录用户模型
class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TaskCreate(BaseModel):
    title: str
    description: str | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    user_id: int
    created_at: datetime
    updated_at: datetime

class LoginLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    ip: str
    user_agent: str
    success: bool
    created_at: datetime

class AdminUserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_locked: bool
    lock_until: Optional[datetime]
    created_at: datetime
