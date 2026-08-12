---
title: Python 生产环境上线 Checklist
date: 2026-08-22 13:45:00
tags:
  - Python
  - 生产环境
  - Checklist
categories:
  - Python 生产环境
---

## 上线 Checklist

### 代码与依赖

- [ ] requirements.txt / poetry.lock 已锁定
- [ ] pip-audit / bandit CI 通过
- [ ] 测试覆盖率 ≥ 80%
- [ ] debug=False，docs 关闭或鉴权

### 部署

- [ ] Docker 多阶段、非 root 用户
- [ ] Gunicorn/Uvicorn worker 数已规划
- [ ] K8s requests/limits 已配置
- [ ] liveness `/health` + readiness `/ready`
- [ ] graceful shutdown 验证

### 配置与安全

- [ ] 密钥来自 Secret/Vault，无硬编码
- [ ] CORS 白名单
- [ ] HTTPS（Ingress/Nginx）
- [ ] 数据库连接池 + 总连接数评审

### 可观测

- [ ] JSON 结构化日志 → 集中采集
- [ ] Prometheus `/metrics` + Grafana
- [ ] 5xx、延迟、队列积压告警
- [ ] request_id 贯穿

### 容错

- [ ] 外部 HTTP 调用有 timeout
- [ ] 重试有上限（幂等场景）
- [ ] Celery 任务有 max_retries
- [ ] 回滚方案验证（≤ 5 分钟）

### CI/CD

- [ ] main 分支 CI 绿
- [ ] 镜像 tag = git sha
- [ ] staging 验证通过
- [ ] On-Call 知晓发布窗口

---

## 日常 Runbook 速查

| 场景 | 动作 |
|------|------|
| 5xx 突增 | 查部署时间 → 回滚或查日志 |
| OOMKilled | 升 memory limit / 减 worker |
| 慢响应 | profile + 慢查询 + 缓存 |
| Celery 积压 | 扩 worker / 查 poison task |
| DB 连接满 | 减 pool / PgBouncer |

---

**Python 生产环境系列 20 篇**完结，涵盖部署、Docker/K8s、配置、日志、监控、安全、Celery、CI/CD、连接池、容错与排障。建议配合 **Python 新手入门**、**PostgreSQL SRE** 系列对照阅读。
