from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from typing import Optional
from .schemas import AdminUserResponse, TaskResponse, LoginLogResponse
from .database import get_db
from .models import User, Task, LoginLog
from .dependencies import require_admin

router = APIRouter(prefix="/admin", tags=['管理员'])

# 用户管理
@router.get("/users", response_model=list[AdminUserResponse])
async def get_all_users(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    result = await db.execute(select(User).order_by(User.id).offset(skip).limit(limit))
    users = result.scalars().all()
    return [
        AdminUserResponse(
            id = u.id,
            username = u.username,
            role = u.role,
            is_locked = u.is_locked,
            lock_until = u.lock_until,
            created_at = u.created_at
        )
        for u in users
    ]
@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    return AdminUserResponse(
        id = user.id,
        username = user.username,
        role = user.role,
        is_locked = user.is_locked,
        lock_until = user.lock_until,
        created_at = user.created_at
    )
@router.patch("/users/{user_id}/unlock")
async def unlock_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    user.is_locked = False
    user.lock_until = None
    await db.commit()
    return {f"用户{user.username}已解锁"}
@router.delete("/users/{user_id}")
async def delete_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="不能删除自己"
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    await db.delete(user)
    await db.commit()
    return {"msg": f"用户: {user.username}已删除"}
# 任务管理
@router.get("/tasks", response_model=list[TaskResponse])
async def get_all_tasks(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        status: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """获取所有用户的任务列表（仅管理员）"""
    query = select(Task)

    if status:
        query = query.where(Task.status == status)

    query = query.order_by(Task.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        TaskResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status,
            user_id=t.user_id,
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in tasks
    ]


@router.delete("/tasks/{task_id}")
async def delete_task(
        task_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """删除任意任务（仅管理员）"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    await db.delete(task)
    await db.commit()

    return {"msg": "任务已删除"}

# 登录日志
@router.get("/login-logs", response_model=list[LoginLogResponse])
async def get_login_logs(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        username: Optional[str] = None,
        success: Optional[bool] = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """获取登录日志（仅管理员）"""
    query = select(LoginLog)

    if username:
        query = query.where(LoginLog.username == username)
    if success is not None:
        query = query.where(LoginLog.success == success)

    query = query.order_by(LoginLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        LoginLogResponse(
            id=log.id,
            user_id=log.user_id,
            username=log.username,
            ip=log.ip,
            user_agent=log.user_agent,
            success=log.success,
            created_at=log.created_at
        )
        for log in logs
    ]

# 仪表盘统计
@router.get("/stats")
async def get_stats(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """获取系统统计信息（仅管理员）"""
    # 用户总数
    user_count_result = await db.execute(select(func.count()).select_from(User))
    total_users = user_count_result.scalar()

    # 任务总数
    task_count_result = await db.execute(select(func.count()).select_from(Task))
    total_tasks = task_count_result.scalar()

    # 今日登录次数
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    today_login_result = await db.execute(
        select(func.count()).select_from(LoginLog).where(
            LoginLog.created_at >= today_start,
            LoginLog.success == True
        )
    )
    today_logins = today_login_result.scalar()

    # 锁定用户数
    locked_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_locked == True)
    )
    locked_users = locked_result.scalar()

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "today_logins": today_logins,
        "locked_users": locked_users
    }


