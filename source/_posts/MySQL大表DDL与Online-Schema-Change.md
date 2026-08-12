---
title: MySQL 大表 DDL 与 Online Schema Change
date: 2026-08-14 13:00:00
tags:
  - MySQL
  - DDL
categories:
  - MySQL SRE
---

大表直接 `ALTER TABLE` 可能**锁表数小时**，SRE 必须规范 DDL 流程。

## 原生 Online DDL

MySQL 8.0 多数 InnoDB DDL 支持 INPLACE：

```sql
ALTER TABLE big_table ADD INDEX idx_col (col), ALGORITHM=INPLACE, LOCK=NONE;
```

验证：

```sql
SELECT * FROM performance_schema.metadata_locks;
```

## pt-online-schema-change

```bash
pt-online-schema-change \
  --alter "ADD COLUMN new_col INT" \
  D=mydb,t=big_table \
  --execute
```

原理：触发器/sync 复制到新表 → 原子 rename。

## gh-ost

GitHub 开源，无触发器，基于 binlog：

```bash
gh-ost --user=root --host=... --database=mydb --table=big_table \
  --alter="ADD INDEX idx (col)" --execute
```

## SRE 规范

- 大表 DDL **禁止**直接生产执行未经评审
- 低峰窗口 + 限流 + 监控复制延迟
- 准备 `KILL` gh-ost/pt-osc 回滚步骤
- 先在 shadow 表 / staging 验证耗时

## 风险

- 磁盘空间（新表临时占双倍）
- 主从延迟飙升
- 长事务阻塞 OSC  cutover

DDL 是 MySQL **最高危变更类型**之一。
