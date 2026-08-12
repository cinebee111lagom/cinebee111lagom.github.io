---
title: MySQL InnoDB 生产参数基线
date: 2026-08-14 10:00:00
tags:
  - MySQL
  - InnoDB
categories:
  - MySQL SRE
---

InnoDB 参数决定 MySQL **性能与数据安全**，SRE 需维护统一基线。

## 内存相关

```ini
innodb_buffer_pool_size = 48G          # 物理内存 60~70%
innodb_buffer_pool_instances = 8       # 每实例 ≥ 1GB
innodb_log_buffer_size = 64M
```

## 日志与持久化

```ini
innodb_redo_log_capacity = 4G          # MySQL 8.0.30+
innodb_flush_log_at_trx_commit = 1     # 最高安全
sync_binlog = 1
```

| flush 组合 | 安全性 | TPS |
|------------|--------|-----|
| trx=1, sync=1 | 最高 | 较低 |
| trx=2, sync=1 | 高 | 中 |
| trx=2, sync=0 | 低 | 高 |

## IO 与并发

```ini
innodb_io_capacity = 2000
innodb_io_capacity_max = 4000
innodb_read_io_threads = 8
innodb_write_io_threads = 8
innodb_thread_concurrency = 0        # 默认不限制
```

## 连接

```ini
max_connections = 2000
max_connect_errors = 100000
wait_timeout = 600
interactive_timeout = 600
```

## 表空间

```ini
innodb_file_per_table = ON
innodb_default_row_format = DYNAMIC
```

## 变更原则

- 参数变更写入**配置基线文档**
- 生产变更需 staging 验证 + 维护窗口
- 禁止无文档的 `SET GLOBAL` 临时改后不回收

参数基线是 MySQL SRE **第一道质量门**。
