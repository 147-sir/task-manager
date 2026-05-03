from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import DateTime, func, Integer, String, TEXT, Boolean, Enum as SQLEnum, ForeignKey, TIMESTAMP
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now, comment='创建时间')
    updated_at: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now, onupdate=func.now(), comment='更新时间')

class User(Base):
    __tablename__='users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='用户ID')
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment='用户名')
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment='密码')
    role: Mapped[str] = mapped_column(String(20), default='user', comment='角色')
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, comment='是否锁定')
    lock_until: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True, comment='锁定截止时间')
    tasks: Mapped[list['Task']] = relationship('Task', back_populates='user', lazy='selectin')
    refresh_tokens: Mapped[list['RefreshToken']] = relationship('RefreshToken', back_populates='user', lazy='selectin')
    login_logs: Mapped[list["LoginLog"]] = relationship("LoginLog", back_populates="user", lazy="selectin")

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='任务ID')
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment='任务标题')
    description: Mapped[str] = mapped_column(TEXT, comment='任务描述')
    status: Mapped[str] = mapped_column(SQLEnum('pending', 'completed', name='status_enum'), default='pending', comment='状态')
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, comment='所属用户')
    user: Mapped['User'] = relationship('User', back_populates='tasks')

class RefreshToken(Base):
    __tablename__='refresh_tokens'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='刷新令牌ID')
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment='刷新令牌')
    expire_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment='过期时间')
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, comment='是否有效')
    user: Mapped['User'] = relationship('User', back_populates='refresh_tokens')

class LoginLog(Base):
    __tablename__ = 'login_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='ID')
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True, comment='用户ID（登录成功时有值）')
    username: Mapped[str] = mapped_column(String(255), nullable=False, comment='登录时输入的用户名')
    ip: Mapped[str] = mapped_column(String(45), nullable=False, comment='客户端IP')
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment='User-Agent')
    success: Mapped[bool] = mapped_column(Boolean, default=False, comment='是否登录成功')
    user: Mapped[Optional["User"]] = relationship("User", back_populates="login_logs")