---
title: MySQL InnoDB 性能调优实战
date: 2026-08-14 12:45:00
tags:
  - MySQL
  - 性能
categories:
  - MySQL SRE
---

## Buffer Pool 调优

```sql
SELECT (PagesData * PageSize) / 1024 / 1024 / 1024 AS data_gb
FROM (
  SELECT variable_value AS PagesData FROM performance_schema.global_status
  WHERE variable_name = 'Innodb_buffer_pool_pages_data'
) a,
( SELECT variable_value AS PageSize FROM performance_schema.global_status
  WHERE variable_name = 'Innodb_page_size' ) b;
```

目标：热数据命中率 > 99%。

## Redo Log

```ini
innodb_redo_log_capacity = 4G   # 大写入 workload 可 8G+
```

redo 太小 → checkpoint 频繁 → 抖动。

## 锁与事务

```sql
SELECT * FROM sys.innodb_lock_waits;
SELECT * FROM performance_schema.data_locks;
```

- 大事务拆小
- 索引避免 gap lock 扩散
- RC 隔离级别减少锁（评估业务）

## IO 瓶颈

- `iostat` 看 %util
- 升 SSD/NVMe
- `innodb_flush_neighbors = 0`（SSD）

## 只读扩展

- 读走 Replica + ProxySQL 权重
- 避免复制延迟读旧数据（关键读走主）

## 压测

```bash
sysbench oltp_read_write --mysql-host=... --tables=10 --table-size=1000000 prepare
sysbench ... run
```

调优需**数据驱动**：先看监控，再改参数，避免迷信「万能配置」。
