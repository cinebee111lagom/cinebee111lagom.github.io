---
title: Python 生产故障排查与 Runbook
date: 2026-08-22 13:30:00
tags:
  - Python
  - 故障排查
  - Runbook
categories:
  - Python 生产环境
---

Python 生产故障排查需结合日志、指标、进程状态快速定位。

## 常见故障

| 现象 | 可能原因 |
|------|----------|
| 502/504 | worker 全挂、超时、反代配置 |
| 5xx 突增 | 下游 DB/Redis 故障、代码 bug |
| OOMKilled | 内存 limit 低、泄漏、worker 过多 |
| 响应慢 | N+1 查询、缺索引、无缓存 |
| Celery 积压 | worker 不足、任务卡住 |

## 排查命令

```bash
# K8s
kubectl logs deployment/myapp-api --tail=200
kubectl describe pod <pod>
kubectl top pod

# 容器内
ps aux | grep gunicorn
curl localhost:8000/health
curl localhost:8000/metrics

# 进程
py-spy top --pid $(pgrep -f gunicorn | head -1)
```

## 日志关联

```
request_id: abc-123  →  OpenSearch/Loki 全文搜
trace_id → Jaeger 链路
```

## DB 连接打满

```sql
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```

→ 减 pool_size、查连接泄漏、扩 max_connections。

## 紧急回滚

```bash
kubectl rollout undo deployment/myapp-api
# 或
kubectl set image deployment/myapp-api api=registry.example.com/myapp:<prev-sha>
```

## Runbook 模板

```markdown
## 告警：myapp 5xx rate > 1%
1. 查看 Grafana 5xx 曲线与部署时间
2. 若刚发布 → 回滚
3. 查日志 ERROR 堆栈
4. 检查 DB/Redis 健康
5. 扩容 HPA（若是流量突增）
6. Escalate on-call L2
```

## Postmortem

- 时间线
- 根因
- 修复动作
- 预防项（测试、监控、限流）

**先恢复服务，再根因分析**。
