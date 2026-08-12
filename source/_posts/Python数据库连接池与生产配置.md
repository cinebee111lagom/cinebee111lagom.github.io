---
title: Python 数据库连接池与生产配置
date: 2026-08-22 12:45:00
tags:
  - Python
  - 数据库
  - 连接池
categories:
  - Python 生产环境
---

生产环境必须用**连接池**，避免每请求新建连接打爆数据库。

## SQLAlchemy 2.0 异步

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host:5432/db",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

## 连接数规划

```
总连接 ≈ API replicas × workers × pool_size
       + Celery workers × pool_size

需 < PostgreSQL max_connections × 0.8
```

例：3 Pod × 2 worker × 20 pool = 120 连接

## 与 PgBouncer 配合

```
App pool_size=10 → PgBouncer → PostgreSQL
```

微服务多时**必须 PgBouncer**，见 PostgreSQL SRE 系列。

## 同步 SQLAlchemy

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)
```

## Redis 连接池

```python
import redis.asyncio as redis

redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,
    decode_responses=True,
)
r = redis.Redis(connection_pool=redis_pool)
```

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| Too many connections | pool 过大 | 减 pool + PgBouncer |
| 连接泄漏 | 未 close session | 用 context manager |
| 断连 | 空闲超时 | pool_pre_ping=True |

## Checklist

- [ ] pool_size 已文档化
- [ ] 总连接数 DB 侧可承受
- [ ] pool_pre_ping 开启
- [ ] 慢查询监控

数据库是 Python API **最常见的生产瓶颈**。
