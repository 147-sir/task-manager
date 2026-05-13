from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import timezone, datetime
from app.db.database import get_db
from app.models.models import User, Task, LoginLog
from app.schemas.schemas import AdminUserResponse, TaskResponse, LoginLogResponse
from app.core.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["管理员"])

# 用户管理
@router.get("/users", response_model=list[AdminUserResponse])
async def get_all_users(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
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
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
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
@router.patch("/unlock/{user_id}")
async def unlock_user(
        user_id: int,
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
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
    return {f"用户:{user.username}已解锁"}

@router.delete("/{user_id}")
async def delete_user(
        user_id: int,
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
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

@router.get("/tasks", response_model=list[TaskResponse])
async def get_all_tasks(
        skip: int = Query(0, ge=0),
        limit: int =Query(100, ge=1,le=1000),
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).order_by(Task.created_at.desc()).offset(skip).limit(limit))
    tasks = result.scalars().all()
    return [
        TaskResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            user_id=t.user_id,
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in tasks
    ]

@router.delete("/{task_id}")
async def delete_task(
        task_id: int,
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在"
        )
    await db.delete(task)
    await db.commit()
    return {"msg": f"任务: {task.title}已删除"}

@router.get("/logs", response_model=list[LoginLogResponse])
async def get_logs(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LoginLog).order_by(LoginLog.created_at.desc()).offset(skip).limit(limit))
    logs = result.scalars().all()
    return [
        LoginLogResponse(
            id = l.id,
            user_id = l.user_id,
            ip = l.ip,
            user_agent = l.user_agent,
            success = l.success,
            created_at = l.created_at
        )
        for l in logs
    ]

@router.get("/states")
async def get_states(
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
):
    user_count = await db.execute(select(func.count()).select_from(User))
    total_users = user_count.scalar()

    task_count = await db.execute(select(func.count()).select_from(Task))
    total_tasks = task_count.scalar()

    total_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    total_login = await db.execute(select(func.count()).select_from(LoginLog).where(
        LoginLog.created_at >= total_start,
        LoginLog.success == True
    ))
    today_logins = total_login.scalar()

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "total_login": today_logins
    }

