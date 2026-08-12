---
title: MySQL 监控体系：Prometheus 与 mysqld_exporter
date: 2026-08-14 10:45:00
tags:
  - MySQL
  - 监控
categories:
  - MySQL SRE
---

MySQL 监控覆盖**可用性、复制、性能、容量**四个维度。

## 部署 mysqld_exporter

```bash
export DATA_SOURCE_NAME="exporter:pass@(10.0.1.10:3306)/"
mysqld_exporter --web.listen-address=:9104
```

创建 exporter 账号：

```sql
CREATE USER 'exporter'@'10.0.%' IDENTIFIED BY 'pass' WITH MAX_USER_CONNECTIONS 3;
GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'10.0.%';
```

## 核心指标

| 指标 | 含义 |
|------|------|
| `mysql_up` | 实例存活 |
| `mysql_global_status_threads_connected` | 连接数 |
| `mysql_global_status_slow_queries` | 慢查询累计 |
| `mysql_slave_status_slave_sql_running` | SQL 线程 |
| `mysql_slave_status_seconds_behind_master` | 复制延迟 |
| `mysql_global_status_innodb_buffer_pool_pages_free` | BP 空闲页 |

## Performance Schema

```sql
SELECT * FROM sys.schema_tables_with_full_table_scans LIMIT 10;
SELECT * FROM sys.statements_with_runtimes_in_95th_percentile LIMIT 10;
```

## Grafana

- Dashboard：7362（MySQL Overview）
- 分屏：QPS/TPS、InnoDB、复制、锁等待

## 日志

```ini
slow_query_log = ON
long_query_time = 0.5
log_queries_not_using_indexes = ON
```

慢日志 → Loki/ELK，配合 PMM 或 Yearning 审计。

监控要**先于用户发现故障**。
