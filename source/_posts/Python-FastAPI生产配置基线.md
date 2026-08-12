---
title: Python FastAPI 生产配置基线
date: 2026-08-22 10:15:00
tags:
  - Python
  - FastAPI
categories:
  - Python 生产环境
---

FastAPI 生产部署需配置生命周期、中间件、文档开关与健康检查。

## 应用入口

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from myapp.core.config import settings
from myapp.core.logging import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # 启动：连接池初始化
    yield
    # 关闭：释放连接

app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)
```

生产关闭 `/docs` 或加认证。

## 中间件

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 健康检查

```python
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    # 检查 DB、Redis
    await check_db()
    return {"status": "ready"}
```

K8s：`/health` → liveness，`/ready` → readiness。

## 全局异常

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.exception("unhandled error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
```

生产不暴露堆栈给客户端。

## 依赖注入 DB

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db():
    async with session_factory() as session:
        yield session

@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    ...
```

## 生产 Checklist

- [ ] debug=False
- [ ] docs 关闭或鉴权
- [ ] CORS 白名单
- [ ] 健康检查端点
- [ ] 请求 ID 中间件（可选）

FastAPI + Uvicorn Worker 是当前 Python API 生产主流组合。
