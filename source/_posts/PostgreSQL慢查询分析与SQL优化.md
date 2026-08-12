---
title: PostgreSQL 慢查询分析与 SQL 优化
date: 2026-08-15 11:15:00
tags:
  - PostgreSQL
  - 慢查询
  - 性能
categories:
  - PostgreSQL SRE
---

PostgreSQL 慢查询分析依赖 pg_stat_statements、EXPLAIN 与 auto_explain。

## 启用 pg_stat_statements

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

SELECT query, calls,
       round(mean_exec_time::numeric, 2) AS avg_ms,
       round(total_exec_time::numeric, 2) AS total_ms,
       rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

## EXPLAIN 分析

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders WHERE user_id = 123 AND created_at > '2026-01-01';
```

关注：
- **Seq Scan** 大表 → 缺索引
- **Nested Loop** 行数爆炸 → JOIN 条件或统计信息过期
- **Buffers: shared hit/read** → 缓存命中率

## auto_explain（自动记录慢 SQL）

```ini
shared_preload_libraries = 'pg_stat_statements, auto_explain'
auto_explain.log_min_duration = 500
auto_explain.log_analyze = on
auto_explain.log_buffers = on
```

## 常见优化手段

| 问题 | 方案 |
|------|------|
| 缺索引 | `CREATE INDEX CONCURRENTLY` |
| 统计过期 | `ANALYZE table` 或提高 `default_statistics_target` |
| 大 IN 列表 | 改 JOIN 或临时表 |
| 函数包裹列 | 表达式索引 |
| 分页深翻 | Keyset pagination（`WHERE id > last_id`） |

## 索引建议

```sql
-- 未使用索引
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%pkey%';
```

## vacuum 与 bloat

```sql
SELECT schemaname, relname, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

dead tuple 过多导致 Seq Scan 变慢，检查 autovacuum 是否跟得上。

## SRE 流程

1. 告警/巡检发现慢 SQL Top N
2. EXPLAIN 定位计划问题
3. 与开发评审索引/改写
4. `CREATE INDEX CONCURRENTLY` 低峰执行
5. 对比优化前后 pg_stat_statements

禁止生产直接 `EXPLAIN ANALYZE` 写操作，用只读副本或事务 rollback 测试。
