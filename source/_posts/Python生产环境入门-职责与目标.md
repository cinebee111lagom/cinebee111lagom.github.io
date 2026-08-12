---
title: Python 生产环境入门：职责与目标
date: 2026-08-22 09:00:00
tags:
  - Python
  - 生产环境
categories:
  - Python 生产环境
---

Python 在生产中常用于 Web API、任务队列、数据管道与运维自动化，目标是**稳定、可观测、可回滚**地运行。

## 生产 vs 开发

| 维度 | 开发 | 生产 |
|------|------|------|
| 依赖 | 随意 pip install | 锁定版本、审计漏洞 |
| 配置 | .env 本地 | 密钥管理、环境隔离 |
| 进程 | `python app.py` | Gunicorn/Uvicorn + 多 worker |
| 日志 | print | 结构化 JSON + 集中采集 |
| 错误 | 堆栈直接暴露 | 统一处理、告警 |

## 生产职责

| 领域 | 内容 |
|------|------|
| 部署 | Docker/K8s、蓝绿/滚动发布 |
| 运行时 | WSGI/ASGI 服务器、worker 数 |
| 依赖 | requirements.lock、虚拟环境 |
| 配置 | 12-Factor、Secret 管理 |
| 可观测 | 日志、指标、链路追踪 |
| 安全 | 依赖扫描、最小权限 |
| 容量 | CPU/内存、连接池、并发 |

## SLA 参考

| 指标 | 目标 |
|------|------|
| 可用性 | 99.9% ~ 99.95% |
| API P99 延迟 | < 200ms（视业务） |
| 错误率 | < 0.1% |
| 部署 RTO | ≤ 15 分钟回滚 |

## 架构演进

```
python app.py → Gunicorn + Nginx → Docker → K8s + HPA
             → Celery 异步 → CI/CD + 监控告警
```

## 与开发边界

- **开发**：业务逻辑、API 设计、单元测试
- **平台/SRE**：镜像、部署、监控、扩缩容
- **安全**：漏洞扫描、网络策略

本系列 20 篇覆盖 Python 从打包、部署、配置、日志、监控到上线 Checklist 的完整生产路径。
