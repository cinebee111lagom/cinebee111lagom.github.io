---
title: Python 性能调优与 profiling 生产实践
date: 2026-08-22 12:00:00
tags:
  - Python
  - 性能
categories:
  - Python 生产环境
---

Python 性能调优需先 **profile 定位瓶颈**，再针对性优化。

## profiling 工具

```bash
# cProfile
python -m cProfile -o out.prof app.py
pip install snakeviz && snakeviz out.prof

# 行级
pip install py-spy
py-spy top --pid <pid>
py-spy record -o profile.svg --pid <pid>
```

## 常见瓶颈

| 瓶颈 | 方案 |
|------|------|
| CPU 密集循环 | NumPy/Cython/多进程 |
| I/O 等待 | async/await、连接池 |
| ORM N+1 | joinedload、批量查询 |
| 大 JSON 序列化 | orjson |
| GIL 限制 | 多 worker 进程 |

## async 数据库

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

## 缓存

```python
import redis
cache = redis.from_url(settings.redis_url)

async def get_user(user_id: str):
    key = f"user:{user_id}"
    if cached := cache.get(key):
        return json.loads(cached)
    user = await db.fetch_user(user_id)
    cache.setex(key, 300, json.dumps(user))
    return user
```

## orjson 加速

```python
import orjson
from fastapi.responses import ORJSONResponse

app = FastAPI(default_response_class=ORJSONResponse)
```

## worker 调优

```
CPU 密集：workers = 2×CPU+1，sync worker
I/O 密集：workers = CPU，UvicornWorker + async
```

## 生产原则

1. 有 metrics 再优化（P99、CPU）
2. 不要过早优化
3. 压测验证（locust、k6）

```bash
pip install locust
locust -f locustfile.py --host=http://localhost:8000
```

**Measure first, optimize second**。
