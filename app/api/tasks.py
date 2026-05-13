from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User, Task
from app.db.database import get_db
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/tasks", tags=['任务管理'])

# 创建任务
@router.post("/", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_task = Task(
        title = task_data.title,
        description = task_data.description,
        user_id = current_user.id
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

# 查询任务
@router.get("/", response_model=list[TaskResponse])
async def get_tasks(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.user_id == current_user.id).order_by(Task.created_at.desc()))
    return result.scalars().all()

# 获取单个任务
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在"
        )
    return task

# 修改任务
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
        task_id: int,
        task_data: TaskUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在"
        )
    update_data = task_data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(task, k, v)
    await db.commit()
    await db.refresh(task)
    return task

# 删除任务
@router.delete("/{task_id}")
async def del_task(
        task_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code = 404,
            detail = "任务不存在"
        )
    await db.delete(task)
    await db.commit()
    return {"message": "删除成功"}

