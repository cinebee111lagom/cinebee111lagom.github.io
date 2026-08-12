---
title: Python 异步任务与 Celery 生产部署
date: 2026-08-22 12:15:00
tags:
  - Python
  - Celery
  - 异步
categories:
  - Python 生产环境
---

耗时任务应异步化，**Celery + Redis/RabbitMQ** 是 Python 生产标配。

## 架构

```
FastAPI → 投递任务 → Redis Broker → Celery Worker
                                  ← Beat 定时
                                  → Flower 监控
```

## Celery 配置

```python
# tasks/celery_app.py
from celery import Celery

celery_app = Celery(
    "myapp",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "myapp.tasks.send_email": {"queue": "email"},
        "myapp.tasks.generate_report": {"queue": "heavy"},
    },
)

@celery_app.task(bind=True, max_retries=3)
def send_email(self, to: str, subject: str):
    try:
        ...
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

## Worker 启动

```bash
celery -A myapp.tasks.celery_app worker -Q email,heavy -c 4 -l info
celery -A myapp.tasks.celery_app beat -l info
celery -A myapp.tasks.celery_app flower --port=5555
```

## K8s 分离部署

| 组件 | Deployment |
|------|------------|
| API | myapp-api |
| Worker | myapp-worker（可 HPA） |
| Beat | myapp-beat（单副本） |

## 监控

- Flower UI：队列长度、任务状态
- Prometheus：`celery_task_sent_total`、`celery_task_failed_total`
- 告警：队列积压 > 阈值

## 最佳实践

| 项 | 建议 |
|----|------|
| 幂等 | 任务可安全重试 |
| 超时 | `task_time_limit=300` |
| 结果 | 大结果存 S3，非 Redis |
| 死信 | 失败 N 次进 DLQ |

API 快速返回，重活交给 Celery。
