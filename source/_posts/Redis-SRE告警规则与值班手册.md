---
title: Redis SRE 告警规则与值班手册
date: 2026-08-13 16:30:00
tags:
  - Redis
  - 告警
  - SRE
categories:
  - Redis SRE
---

告警要少而准，值班手册要**可执行**。

## P0 告警（立即响应）

```yaml
# Prometheus 规则示例
- alert: RedisDown
  expr: redis_up == 0
  for: 1m
  labels:
    severity: critical

- alert: RedisMemoryHigh
  expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
  for: 5m

- alert: RedisReplicationBroken
  expr: redis_connected_slaves == 0 and redis_instance_role == "master"
  for: 2m
```

## P1 告警（30 分钟内）

- 命中率 < 80% 持续 15m
- 连接数 > maxclients 80%
- 主从 offset 差 > 10MB 持续 5m
- 慢查询 QPS 突增

## 值班 Runbook 摘要

| 告警 | 第一步 | 第二步 |
|------|--------|--------|
| RedisDown | 检查进程/容器 | 查日志 OOM/Kill |
| MemoryHigh | 看 evicted_keys | 扩容或清大 key |
| ReplicationBroken | 网络/密码 | `INFO replication` |
| Failover 事件 | 确认新主 | 旧主 rejoin 为从 |

## 通知路由

```
P0 → 电话 + IM + 工单
P1 → IM + 工单
P2 → 工单（次日处理）
```

## 告警反模式

- ❌ 每个指标都告警
- ❌ 无 runbook 链接
- ❌ 告警风暴无聚合（用 Alertmanager inhibit）

每季度**告警演练**：故意触发 failover，验证通知与响应时间。
