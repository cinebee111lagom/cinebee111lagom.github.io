---
title: Python 生产部署架构选型
date: 2026-08-22 09:15:00
tags:
  - Python
  - 架构
categories:
  - Python 生产环境
---

Python 生产部署需根据 QPS、团队技能与基础设施选型。

## 常见形态

| 形态 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| 裸机 + systemd | 小规模、遗留 | 简单 | 难扩缩 |
| Docker + Compose | 中小团队 | 环境一致 | 单机 HA 弱 |
| K8s Deployment | 云原生 | 弹性、GitOps | 复杂度高 |
| PaaS（Railway/Fly.io） | 初创 | 快 | 定制受限 |
| Serverless | 低频 API | 免运维 | 冷启动、限制多 |

## Web 服务栈

```
客户端 → Nginx/Ingress（TLS、限流）
      → Gunicorn/Uvicorn（多 worker）
      → FastAPI/Flask/Django
      → PostgreSQL / Redis
```

## 同步 vs 异步

| | WSGI (Gunicorn) | ASGI (Uvicorn) |
|---|-----------------|----------------|
| 框架 | Flask、Django | FastAPI、Starlette |
| 并发 | 多进程 worker | async + 多 worker |
| I/O 密集 | 一般 | 优秀 |

## 后台任务

```
API 服务 ←→ Redis/RabbitMQ ←→ Celery Worker
                              ←→ Beat 定时
```

CPU 密集任务考虑独立 worker 池或队列削峰。

## 选型决策

```
QPS < 500，团队 < 5 人？
  ├─ 是 → Docker Compose + Gunicorn
  └─ 否 → K8s + HPA + 分离 Worker
```

## 版本

- 生产 **Python 3.11/3.12**
- 基础镜像 `python:3.12-slim` 或 `distroless`

架构文档应包含：部署拓扑、worker 公式、依赖服务、回滚策略。
