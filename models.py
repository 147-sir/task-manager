from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func, Integer, String, TEXT, Enum as SQLEnum, ForeignKey
from datetime import datetime

class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now, comment='创建时间')
    updated_at: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now, onupdate=func.now(), comment='更新时间')

class User(Base):
    __tablename__='users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='用户ID')
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment='用户名')
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment='密码')
    email: Mapped[str] = mapped_column(String(255), comment='邮箱')

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='任务ID')
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment='任务标题')
    description: Mapped[str] = mapped_column(TEXT, comment='任务描述')
    status: Mapped[str] = mapped_column(SQLEnum('pending', 'completed', name='status_enum'), default='pending', comment='状态')
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, comment='所属用户')