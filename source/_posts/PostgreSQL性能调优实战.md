---
title: PostgreSQL 性能调优实战
date: 2026-08-15 12:45:00
tags:
  - PostgreSQL
  - 性能调优
categories:
  - PostgreSQL SRE
---

PostgreSQL 性能调优围绕内存、I/O、VACUUM、索引与查询计划。

## 内存调优

```ini
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 16MB
maintenance_work_mem = 512MB
```

验证缓存命中：

```sql
SELECT sum(heap_blks_hit) / nullif(sum(heap_blks_hit + heap_blks_read), 0) AS hit_ratio
FROM pg_statio_user_tables;
-- 目标 > 99%
```

## I/O 与 WAL

```ini
random_page_cost = 1.1      # SSD
effective_io_concurrency = 200
wal_compression = on
max_wal_size = 4GB
```

## VACUUM 与 bloat

```sql
-- 表膨胀检查
SELECT schemaname, relname, n_live_tup, n_dead_tup,
       round(n_dead_tup * 100.0 / nullif(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;
```

长事务会阻止 vacuum：

```sql
SELECT pid, xact_start, query FROM pg_stat_activity
WHERE state = 'idle in transaction' ORDER BY xact_start;
```

## 索引优化

```sql
-- 重复/冗余索引
SELECT indrelid::regclass, array_agg(indexrelid::regclass)
FROM pg_index GROUP BY indrelid HAVING count(*) > 3;
```

- BRIN：时序大表
- GIN：jsonb、全文
- 部分索引：`WHERE status = 'active'`

## 并行查询

```ini
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
parallel_tuple_cost = 0.01
```

OLAP 查询受益，OLTP 小查询可能负优化。

## 连接与锁

```sql
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## 调优流程

1. 基线：QPS、P99、hit ratio、复制 lag
2. pg_stat_statements Top SQL
3. EXPLAIN (ANALYZE, BUFFERS)
4. 单变量调参 + 压测对比
5. 文档化变更

性能调优是持续过程，**监控驱动、数据说话**。
