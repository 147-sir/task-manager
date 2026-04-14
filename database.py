import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+asyncmy://root:123456@localhost:3306/task")

async_engine = create_async_engine(
    DATABASE_URL,
    echo = False,
    pool_size = 10
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit= False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("数据库创建完成")