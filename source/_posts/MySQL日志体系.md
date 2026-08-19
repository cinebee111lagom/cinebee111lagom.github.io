---
title: MySQL 日志体系
date: 2026-09-08 02:00:00
tags:
  - MySQL
  - 日志
  - binlog
  - DBA
categories:
  - MySQL
---

MySQL 有多种日志，各自承担不同职责。下面按重要性逐一梳理。

---

## 1. 错误日志（Error Log）

**作用**：记录启动/关闭信息、运行中的错误和警告。

```ini
# my.cnf
[mysqld]
log_error = /var/log/mysql/error.log
log_error_verbosity = 2   # 1=Error, 2=+Warning, 3=+Note
```

```sql
-- 查看路径
SHOW VARIABLES LIKE 'log_error';
```

> 这是排查 MySQL 无法启动、崩溃恢复等问题的第一手资料。

---

## 2. 二进制日志（Binary Log / binlog）

**作用**：记录所有修改数据的语句（DML/DDL），用于**主从复制**和**数据恢复**。

```ini
[mysqld]
server_id         = 1
log_bin           = /var/log/mysql/mysql-bin
binlog_format     = ROW        # ROW | STATEMENT | MIXED
expire_logs_days  = 7
max_binlog_size   = 500M
sync_binlog       = 1          # 每次提交刷盘，最安全
```

### 三种格式对比

| 格式 | 记录内容 | 优点 | 缺点 |
|------|---------|------|------|
| **STATEMENT** | SQL 语句本身 | 日志量小 | 函数(NOW(), RAND())可能不一致 |
| **ROW** | 行变更前后的数据 | 数据一致性最高 | 日志量大 |
| **MIXED** | 自动选择 | 折中 | 行为不可预测 |

### 常用操作

```sql
-- 查看所有 binlog 文件
SHOW BINARY LOGS;

-- 查看某个 binlog 的内容
SHOW BINLOG EVENTS IN 'mysql-bin.000003' LIMIT 20;

-- 命令行解析
mysqlbinlog --start-datetime="2026-08-19 00:00:00" \
            --stop-datetime="2026-08-19 12:00:00" \
            --base64-output=DECODE-ROWS -v \
            mysql-bin.000003

-- 基于 binlog 恢复（跳过误操作）
mysqlbinlog --start-position=154 --stop-position=891 mysql-bin.000003 | mysql -u root -p

-- 刷新 binlog（生成新文件）
FLUSH BINARY LOGS;

-- 清理过期日志
PURGE BINARY LOGS TO 'mysql-bin.000005';
PURGE BINARY LOGS BEFORE '2026-08-01 00:00:00';
```

---

## 3. 重做日志（Redo Log）

**作用**：InnoDB 特有，保证**事务持久性**（WAL 机制：Write-Ahead Logging）。事务提交时先写 redo log，再异步刷数据页。

```ini
[mysqld]
innodb_log_file_size     = 1G      # 单个 redo log 文件大小
innodb_log_files_in_group = 2      # redo log 文件数量（默认循环写）
innodb_flush_log_at_trx_commit = 1 # 每次提交都 fsync（最安全）
```

### 刷盘策略 `innodb_flush_log_at_trx_commit`

| 值 | 行为 | 性能 | 安全性 |
|---|------|------|--------|
| **0** | 每秒写 OS buffer + fsync | 最高 | 可能丢 1 秒数据 |
| **1** | 每次 commit 都 fsync | 最低 | 最安全，不丢数据 |
| **2** | 每次 commit 写 OS buffer，每秒 fsync | 中等 | OS 崩溃可能丢 1 秒 |

---

## 4. 回滚日志（Undo Log）

**作用**：
- 实现事务**回滚**
- 提供 MVCC 所需的**历史版本数据**

```sql
-- 查看 undo 表空间
SHOW VARIABLES LIKE 'innodb_undo%';

-- MySQL 8.0 支持独立 undo 表空间
-- 可以在线 truncate 空闲的 undo 表空间
ALTER UNDO TABLESPACE undo_001 SET INACTIVE;
```

**工作原理**：
```
事务修改数据 → 旧数据写入 undo log → 其他事务通过 undo log 读到旧版本
事务回滚时   → 从 undo log 恢复原始数据
```

---

## 5. 慢查询日志（Slow Query Log）

**作用**：记录执行时间超过阈值的 SQL，是**性能调优**的核心工具。

```ini
[mysqld]
slow_query_log      = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time     = 1          # 超过 1 秒记录
log_queries_not_using_indexes = 1 # 记录未使用索引的查询
min_examined_row_limit = 100     # 扫描行数超过 100 才记录
```

```sql
-- 动态开启
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 0.5;

-- 分析慢日志
-- 方法1: mysqldumpslow（自带工具）
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

-- 方法2: pt-query-digest（Percona Toolkit，更强大）
pt-query-digest /var/log/mysql/slow.log > slow_report.txt
```

**pt-query-digest 输出示例**：
```
Rank  Query ID           Response time  Calls  R/Call   V/M
==== =================== ============== ====== ======== =====
    1 0xABC123...         150.0000  35.2%    200  0.7500  0.12
    2 0xDEF456...          80.0000  18.8%    500  0.1600  0.03
```

---

## 6. 通用查询日志（General Log）

**作用**：记录所有 SQL（包括查询），用于**审计和调试**，生产环境**强烈不建议开启**。

```ini
[mysqld]
general_log      = 1
general_log_file = /var/log/mysql/general.log
```

```sql
-- 临时开启（排查问题时）
SET GLOBAL general_log = ON;
-- 用完立即关闭
SET GLOBAL general_log = OFF;
```

---

## 7. 中继日志（Relay Log）

**作用**：主从复制中，从库接收主库 binlog 后写入 relay log，再由 SQL 线程重放。

```sql
-- 在从库上查看
SHOW RELAYLOG EVENTS;
```

---

## 各日志关系总览

```
┌─────────────────────────────────────────────────────┐
│                    MySQL 日志体系                     │
├──────────┬──────────────────────────────────────────┤
│ Server层 │                                          │
│          │  错误日志 ── 故障排查                      │
│          │  通用日志 ── 审计（慎用）                   │
│          │  慢查询日志 ── 性能优化                    │
│          │  binlog ── 复制 + 恢复                    │
├──────────┼──────────────────────────────────────────┤
│ InnoDB层 │                                          │
│          │  redo log ── 崩溃恢复（持久性）             │
│          │  undo log ── 回滚 + MVCC（隔离性）         │
├──────────┼──────────────────────────────────────────┤
│ 复制相关  │  binlog（主库）→ relay log（从库）         │
└──────────┴──────────────────────────────────────────┘
```

---

## 生产环境推荐配置

```ini
[mysqld]
# 错误日志
log_error            = /var/log/mysql/error.log
log_error_verbosity  = 2

# binlog
log_bin              = /var/log/mysql/mysql-bin
binlog_format        = ROW
sync_binlog          = 1
expire_logs_days     = 7

# redo log
innodb_flush_log_at_trx_commit = 1

# 慢查询
slow_query_log       = 1
slow_query_log_file  = /var/log/mysql/slow.log
long_query_time      = 1

# 通用日志：关闭
general_log          = 0
```

> **核心原则**：`sync_binlog=1` + `innodb_flush_log_at_trx_commit=1` 是双1配置，保证不丢数据但性能稍低；对性能要求高的场景可以适当放松，但要接受极端情况下少量数据丢失的风险。

---

如果你对某类日志想深入了解（比如 binlog 的恢复实操、redo log 的内部结构、慢日志分析方法），可以继续问。
