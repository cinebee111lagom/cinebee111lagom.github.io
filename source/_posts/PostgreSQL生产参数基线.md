---
title: PostgreSQL 生产参数基线
date: 2026-08-15 10:00:00
tags:
  - PostgreSQL
  - 参数调优
categories:
  - PostgreSQL SRE
---

PostgreSQL 参数需按硬件与 workload 调整，以下为 16GB 内存 OLTP 基线参考。

## 内存

```ini
shared_buffers = 4GB              # 物理内存 25%
effective_cache_size = 12GB     # 操作系统缓存估算
work_mem = 16MB                   # 排序/哈希，注意 × 并发连接
maintenance_work_mem = 512MB      # VACUUM、CREATE INDEX
```

## WAL 与检查点

```ini
wal_level = replica
max_wal_size = 4GB
min_wal_size = 1GB
checkpoint_completion_target = 0.9
wal_compression = on
```

## 连接

```ini
max_connections = 200             # 应用直连不宜过大，配合 PgBouncer
superuser_reserved_connections = 3
```

## 复制

```ini
max_wal_senders = 10
max_replication_slots = 10
hot_standby = on
hot_standby_feedback = on
```

## 日志

```ini
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_min_duration_statement = 500  # 慢查询 ms
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
```

##  autovacuum

```ini
autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 30s
autovacuum_vacuum_scale_factor = 0.05
autovacuum_analyze_scale_factor = 0.02
```

## pg_stat_statements

```ini
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.max = 10000
pg_stat_statements.track = all
```

```sql
CREATE EXTENSION pg_stat_statements;
```

## 安全

```ini
ssl = on
password_encryption = scram-sha-256
```

## 调优原则

| 原则 | 说明 |
|------|------|
| 先监控再调 | 用 pg_stat_* 定位瓶颈 |
| 一次改一项 | 便于回滚对比 |
| shared_buffers 非越大越好 | 超过 40% 收益递减 |
| work_mem 慎增 | 高并发 × 大 work_mem = OOM |

参数变更后 `SELECT pg_reload_conf();`，部分需重启（`shared_buffers`、`max_connections`）。
