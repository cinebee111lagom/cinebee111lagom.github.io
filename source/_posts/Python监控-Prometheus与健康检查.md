---
title: Python 监控：Prometheus 与健康检查
date: 2026-08-22 11:30:00
tags:
  - Python
  - Prometheus
  - 监控
categories:
  - Python 生产环境
---

Python 服务需暴露 **Prometheus 指标** 与健康端点，接入 Grafana 告警。

## prometheus-fastapi-instrumentator

```bash
pip install prometheus-fastapi-instrumentator
```

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

暴露 `/metrics` 供 Prometheus scrape。

## 自定义指标

```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency",
    ["endpoint"]
)
```

## Prometheus 配置

```yaml
scrape_configs:
  - job_name: myapp
    metrics_path: /metrics
    static_configs:
      - targets: ["myapp:8000"]
```

## 关键指标

| 指标 | 告警 |
|------|------|
| `http_requests_total{status=~"5.."}` | 5xx 率 P1 |
| `http_request_duration_seconds` P99 | 延迟 P2 |
| 进程内存 / CPU | OOM 预警 |
| Celery queue length | 积压 P1 |

## 健康检查层次

```python
@app.get("/health")   # 进程存活 → liveness
async def health():
    return {"status": "ok"}

@app.get("/ready")    # 依赖就绪 → readiness
async def ready():
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ready"}
```

## 链路追踪（可选）

```bash
pip install opentelemetry-instrumentation-fastapi
```

接入 Jaeger/Tempo，关联 request_id。

## Checklist

- [ ] /metrics 内网 only
- [ ] liveness + readiness 分离
- [ ] 5xx 率告警
- [ ] Grafana Dashboard
- [ ] 告警链 Runbook

**可观测三件套：日志 + 指标 + 追踪**。
