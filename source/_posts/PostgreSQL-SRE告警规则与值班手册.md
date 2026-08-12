---
title: PostgreSQL SRE 告警规则与值班手册
date: 2026-08-15 11:00:00
tags:
  - PostgreSQL
  - SRE
  - 告警
categories:
  - PostgreSQL SRE
---

告警分级与 Runbook 链接是值班效率的关键。

## 告警分级

| 级别 | 场景 | 响应 |
|------|------|------|
| P0 | 主库不可写、全集群 down | 5 分钟内响应 |
| P1 | 复制中断、连接打满、磁盘 >85% | 15 分钟 |
| P2 | 慢查询激增、autovacuum 滞后 | 1 小时 |
| P3 | 备份失败、证书即将过期 | 下一工作日 |

## Prometheus 告警规则示例

```yaml
groups:
  - name: postgresql
    rules:
      - alert: PostgreSQLDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL {{ $labels.instance }} down"

      - alert: PostgreSQLReplicationLag
        expr: pg_stat_replication_replay_lag > 30
        for: 5m
        labels:
          severity: warning

      - alert: PostgreSQLConnectionsHigh
        expr: pg_stat_activity_count / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning

      - alert: PostgreSQLDeadlocks
        expr: increase(pg_stat_database_deadlocks[5m]) > 0
        labels:
          severity: warning
```

## 值班手册速查

### 主库不可写

```bash
systemctl status postgresql
tail -100 /var/log/postgresql/postgresql-*.log
df -h
patronictl list   # 若用 Patroni
```

### 复制中断

```sql
SELECT * FROM pg_stat_replication;
SELECT * FROM pg_replication_slots;
-- 检查 slot 是否 inactive、WAL 是否被删
```

### 连接打满

```sql
SELECT pid, usename, application_name, client_addr, state, query_start, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;
-- pg_terminate_backend(pid) 谨慎使用
```

### 磁盘告警

- 检查 WAL 归档是否堆积
- `VACUUM FULL` 慎用，优先 pg_repack
- 扩容磁盘或清理历史分区

### 死锁

```sql
SELECT * FROM pg_stat_database WHERE datname = 'mydb';
-- 查 log_lock_waits 日志定位 SQL
```

## On-Call 原则

1. 先恢复服务，再根因分析
2. 切换前确认复制延迟
3. 重大变更需两人复核
4. 事故后 48h 内 Postmortem

每季度 review 告警，**减少噪音、提高信噪比**。
