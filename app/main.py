from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.database import init_db
from app.api.auth import router
from app.api.tasks import router as tasks_router
from app.api.admin import router as admin_router
from app.core.redis_client import test_redis
from app.middleware.rate_limit import RateLimitMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("后端启动")
    await init_db()
    test_redis()
    yield
    print("后端关闭")

app = FastAPI(title="Task Manager", lifespan=lifespan)

# 注册限流中间件
app.add_middleware(RateLimitMiddleware)
# 注册路由
app.include_router(router)
app.include_router(tasks_router)
app.include_router(admin_router)
@app.get("/")
def root():
    return {"message": "Hello World"}


