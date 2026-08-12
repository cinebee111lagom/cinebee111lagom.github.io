---
title: Python 错误处理、重试与熔断
date: 2026-08-22 13:00:00
tags:
  - Python
  - 容错
categories:
  - Python 生产环境
---

生产服务需优雅处理下游故障，避免级联雪崩。

## 统一错误响应

```python
from fastapi import HTTPException

class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
```

##  tenacity 重试

```bash
pip install tenacity
```

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def call_external_api():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get("https://api.example.com/data")
        resp.raise_for_status()
        return resp.json()
```

仅对**幂等**或**临时故障**重试。

## 熔断（circuit breaker）

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
def call_payment_service(order_id):
    ...
```

连续失败打开熔断，快速失败保护下游。

## 超时 everywhere

```python
async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
    ...
```

无超时的 HTTP 调用是生产隐患。

## Celery 重试

```python
@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def process_order(self, order_id):
    try:
        ...
    except TransientError as e:
        raise self.retry(exc=e)
```

## 降级

```python
async def get_recommendations(user_id):
    try:
        return await rec_service.fetch(user_id)
    except ServiceUnavailable:
        return get_cached_recommendations(user_id)  # 降级
```

## Checklist

- [ ] 外部调用有 timeout
- [ ] 重试有上限和 backoff
- [ ] 非 2xx 不无限重试
- [ ] 5xx 统一格式、不泄露堆栈
- [ ] 关键路径有降级方案

容错设计是**高可用的应用层实现**。
