---
title: Python 日志与结构化 logging 生产实践
date: 2026-08-22 11:15:00
tags:
  - Python
  - 日志
categories:
  - Python 生产环境
---

生产环境用**结构化 JSON 日志**，便于 ELK/Loki 检索与告警。

## 标准 logging 配置

```python
import logging
import sys
import json
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log["request_id"] = record.request_id
        return json.dumps(log, ensure_ascii=False)

def setup_logging(level="INFO"):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
```

## structlog（推荐）

```bash
pip install structlog
```

```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
log = structlog.get_logger()
log.info("order_created", order_id="123", amount=99.5)
```

## 请求 ID 中间件

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

## 日志级别

| 级别 | 生产用途 |
|------|----------|
| ERROR | 需告警 |
| WARNING | 需关注 |
| INFO | 业务关键路径 |
| DEBUG | 仅 dev/staging |

## 禁止

- `print()` 打生产日志
- 日志中输出密码、token、PII
- 无 rotation 写本地大文件（容器应 stdout）

## 采集

```
Pod stdout → Fluent Bit/Filebeat → OpenSearch/Loki
```

## Checklist

- [ ] JSON 结构化
- [ ] request_id 贯穿
- [ ] 异常带 stack trace
- [ ] 级别 prod=INFO
- [ ] 无敏感信息泄露

好日志是**生产排障的第一数据源**。
