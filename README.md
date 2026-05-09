# Task Manager - 企业级任务管理系统

## 技术栈
- **后端**: FastAPI + SQLAlchemy + MySQL
- **缓存**: Redis (权限缓存、登录失败计数)
- **认证**: JWT + RefreshToken 双令牌
- **安全**: bcrypt 加密、登录失败锁定、接口限流
- **测试**: Locust 压测

## 核心功能
- 用户注册/登录，JWT 认证
- RefreshToken 自动续期
- Redis 缓存用户权限（5分钟过期）
- 登录失败 5 次锁定 15 分钟
- 接口限流（登录 5次/分钟，任务 30次/分钟）
- 任务增删改查，用户数据隔离
- 登录日志审计（IP、时间、设备）

## 项目亮点
1. **高安全**: 双 Token 认证 + 登录锁定 + 限流防暴力破解
2. **高性能**: Redis 缓存权限，减少数据库查询
3. **高可用**: 异步 SQLAlchemy + 连接池
4. **工程化**: 统一异常处理、环境变量隔离、日志系统

## 压测结果
- 5 并发下成功率 100%
- Redis 缓存命中率 100%
- 限流功能正常（429 返回）

## 快速运行

### 1. 启动 Redis (Docker)
```bash
docker run -d --name my-redis -p 6379:6379 redis:7-alpine
```

### 2. 配置环境变量
复制 .env.example 或创建 .env 文件

### 3. 安装依赖
```bash
pip install -r requirements.txt
```
### 4. 启动项目
```bash
uvicorn app.main:app --reload
```
### 5. 访问文档
打开 http://localhost:8000/docs