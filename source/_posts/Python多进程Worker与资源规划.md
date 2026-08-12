---
title: Python 多进程 Worker 与资源规划
date: 2026-08-22 13:15:00
tags:
  - Python
  - 资源规划
categories:
  - Python 生产环境
---

Python 多 worker 模型下，CPU 与内存需精确规划，避免 OOM 与过度上下文切换。

## GIL 与多进程

```
1 worker = 1 Python 进程 = 1 GIL
多 worker → 真并行（多核）
```

async 单进程内并发 I/O，但 CPU 密集仍靠多 worker。

## Worker 公式

```python
import multiprocessing
cpu_count = multiprocessing.cpu_count()

# CPU 密集
workers_cpu = cpu_count * 2 + 1

# I/O 密集（async）
workers_io = cpu_count
```

## 内存估算

```
单 worker 内存 ≈ 基础 100~200MB + 应用堆
总内存 ≈ workers × 单 worker + 系统预留

例：4 worker × 300MB = 1.2GB → 容器 limit 1.5~2GB
```

## K8s resources

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "2"
    memory: "2Gi"    # 防 OOMKill
```

requests 影响调度，limits 防资源争抢。

## Celery concurrency

```bash
# prefork（默认）CPU 任务
celery worker -c 4

# gevent/eventlet I/O 任务（慎用兼容性）
celery worker -P gevent -c 100
```

## Graceful shutdown

```python
# gunicorn.conf.py
graceful_timeout = 30
timeout = 60

# K8s terminationGracePeriodSeconds: 60
# preStop: sleep 5 等待 LB 摘流量
```

## 压测定容量

```bash
locust -f locustfile.py -u 500 -r 50 --run-time 10m
```

观察 CPU、内存、P99、错误率 plateau 点。

## Checklist

- [ ] worker 数与 CPU 匹配
- [ ] 容器 memory limit 已设
- [ ] graceful shutdown 验证
- [ ] HPA 基于 CPU/自定义 metrics

**worker 不是越多越好**，超过 CPU 核数通常收益递减。
