from fastapi import FastAPI
from contextlib import asynccontextmanager
from .database import init_db
from .auth import router
from .tasks import router as tasks_router
from .admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("后端启动")
    await init_db()
    yield
    print("后端关闭")

app = FastAPI(title="Task Manager", lifespan=lifespan)

# 注册路由
app.include_router(router)
app.include_router(tasks_router)
app.include_router(admin_router)
@app.get("/")
def root():
    return {"message": "Hello World"}


