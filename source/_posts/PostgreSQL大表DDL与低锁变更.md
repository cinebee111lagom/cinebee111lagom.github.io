---
title: PostgreSQL 大表 DDL 与低锁变更
date: 2026-08-15 13:00:00
tags:
  - PostgreSQL
  - DDL
categories:
  - PostgreSQL SRE
---

大表 DDL 若不加控制会长时间锁表，生产需用并发索引与在线变更工具。

## CREATE INDEX CONCURRENTLY

```sql
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
```

- 不阻塞读写（两次表扫描，较慢）
- 失败可能留 INVALID 索引：`REINDEX INDEX CONCURRENTLY`

## 加列（PG 11+）

```sql
ALTER TABLE orders ADD COLUMN remark text DEFAULT '';
-- PG 11+ 有 default 的加列不 rewrite 全表（瞬时）
```

## 改列类型 / 大改

```sql
-- 安全方式：新列 + 回填 + 切换
ALTER TABLE orders ADD COLUMN amount_new numeric(18,2);
UPDATE orders SET amount_new = amount::numeric(18,2) WHERE amount_new IS NULL;
-- 分批 UPDATE，避免长事务
ALTER TABLE orders DROP COLUMN amount;
ALTER TABLE orders RENAME COLUMN amount_new TO amount;
```

## pg_repack（在线重组/VACUUM FULL 替代）

```bash
pg_repack -d mydb -t orders --no-order
```

- 需要额外磁盘空间
- 持有 ACCESS EXCLUSIVE 锁时间极短

## pg_partman / 原生分区

```sql
CREATE TABLE events (
  id bigserial,
  created_at timestamptz NOT NULL,
  data jsonb
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2026_08 PARTITION OF events
  FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
```

历史分区 detach + drop，避免大表 DELETE。

## DDL 变更流程

1. staging 验证耗时与锁行为
2. 低峰窗口 + 变更公告
3. 监控 `pg_stat_activity` 锁等待
4. 准备 `pg_cancel_backend` / 回滚脚本
5. 大表优先 CONCURRENTLY / pg_repack

## 禁止操作

- 大表 `VACUUM FULL` 高峰执行
- 无 timeout 的 `ALTER TABLE ... TYPE`
- 生产直接 `DROP COLUMN` 无备份

**原则**：能在线则在线，能分批则分批。
