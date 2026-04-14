from pydantic import BaseModel, Field
from datetime import datetime

# 定义注册用户模型
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: str | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None

# 定义登录用户模型
class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# 创建任务时客户端传的数据格式
class TaskCreate(BaseModel):
    title: str
    description: str | None = None

#更新任务时客户端传的数据格式
class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None

# 返回任务时服务端返回的数据格式
class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None =  None
    status: str
    user_id: int
    created_at: datetime
    updated_at: datetime
