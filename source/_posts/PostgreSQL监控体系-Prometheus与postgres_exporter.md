---
title: PostgreSQL 监控体系：Prometheus 与 postgres_exporter
date: 2026-08-15 10:45:00
tags:
  - PostgreSQL
  - Prometheus
  - 监控
categories:
  - PostgreSQL SRE
---

生产 PostgreSQL 监控以 postgres_exporter + Prometheus + Grafana 为主流方案。

## 部署 postgres_exporter

```bash
DATA_SOURCE_NAME="postgresql://exporter:password@localhost:5432/postgres?sslmode=disable" \
  ./postgres_exporter --web.listen-address=:9187
```

创建只读监控账号：

```sql
CREATE USER exporter WITH PASSWORD 'monitor_pass';
GRANT pg_monitor TO exporter;
```

## 核心指标

| 指标 | 含义 | 告警参考 |
|------|------|----------|
| `pg_up` | 实例存活 | = 0 立即 P0 |
| `pg_stat_replication_replay_lag` | 复制延迟 | > 30s P1 |
| `pg_stat_database_xact_commit` | 事务吞吐 | 突降 50% |
| `pg_stat_database_deadlocks` | 死锁 | > 0 持续 |
| `pg_database_size_bytes` | 库大小 | 磁盘 80% |
| `pg_stat_activity_count` | 连接数 | > max_connections 80% |
| `pg_stat_bgwriter_checkpoints_req` | 请求 checkpoint | 频繁需调 wal |

## pg_stat_statements 慢 SQL

```sql
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

## Grafana Dashboard

推荐社区 Dashboard：
- **9628** — PostgreSQL Database
- **12485** — Patroni Cluster

## 日志采集

```ini
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_min_duration_statement = 500
```

→ Filebeat/Fluent Bit → Loki/ELK，与指标关联 trace。

## 检查清单

- [ ] exporter 使用专用低权限账号
- [ ] 复制延迟、连接数、磁盘 P0/P1 告警
- [ ] pg_stat_statements 已启用
- [ ] Patroni 集群额外监控 REST API
- [ ] 告警带 Runbook 链接

监控不是目的，**可行动的告警**才是 SRE 价值。
