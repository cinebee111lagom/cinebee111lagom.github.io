---
title: MySQL 开启二进制日志Binary Log
date: 2026-09-08 01:45:00
tags:
  - MySQL
  - binlog
  - 主从复制
  - DBA
categories:
  - MySQL
---

## 一、什么是二进制日志

二进制日志（binlog）记录了所有对数据库进行修改的 SQL 语句（如 `INSERT`、`UPDATE`、`DELETE`、`CREATE`、`ALTER` 等），**不记录** `SELECT`、`SHOW` 等只读操作。

主要用途：
- **主从复制**（Master-Slave Replication）
- **数据恢复**（配合 `mysqlbinlog` 工具做基于时间点的恢复）
- **审计**（追踪数据变更历史）

---

## 二、配置方式

### 1. 编辑 MySQL 配置文件

```bash
# Linux 下通常位于：
sudo vim /etc/my.cnf
# 或
sudo vim /etc/mysql/mysql.conf.d/mysqld.cnf
```

### 2. 在 `[mysqld]` 段添加以下配置

```ini
[mysqld]
# ===== 二进制日志配置 =====

# 开启 binlog（必须）
server-id = 1
log-bin = /var/lib/mysql/mysql-bin

# binlog 格式：ROW / STATEMENT / MIXED（推荐 ROW）
binlog_format = ROW

# 单个 binlog 文件最大大小（默认 1G）
max_binlog_size = 512M

# binlog 过期天数（MySQL 8.0.3+ 使用此参数）
binlog_expire_logs_seconds = 604800

# MySQL 5.7 及之前用 expire_logs_days（单位：天）
# expire_logs_days = 7

# 每次事务提交时同步 binlog 到磁盘（最安全）
sync_binlog = 1
```

### 各参数说明

| 参数 | 说明 |
|---|---|
| `server-id` | 服务器唯一 ID，**开启 binlog 必须设置** |
| `log-bin` | binlog 文件路径及前缀名，不指定路径则存放在数据目录 |
| `binlog_format` | `STATEMENT`（记录SQL语句）、`ROW`（记录行变更，默认推荐）、`MIXED`（混合模式）|
| `max_binlog_size` | 单个文件上限，达到后自动切换到新文件 |
| `binlog_expire_logs_seconds` | binlog 自动清理时间（秒），8.0.3+ 推荐用此参数 |
| `sync_binlog` | 每提交多少次事务刷一次磁盘，`1` 表示每次事务都刷盘（最安全，性能略低）|

---

## 三、重启 MySQL 使配置生效

```bash
# systemd 系统
sudo systemctl restart mysqld

# 或（部分发行版）
sudo systemctl restart mysql
```

---

## 四、验证是否开启成功

### 方法一：SQL 命令

```sql
-- 查看 binlog 是否开启及当前状态
SHOW VARIABLES LIKE 'log_bin';
-- 应显示 ON

-- 查看 binlog 格式
SHOW VARIABLES LIKE 'binlog_format';

-- 查看所有 binlog 文件列表
SHOW BINARY LOGS;

-- 查看当前正在写入的 binlog
SHOW MASTER STATUS;
```

示例输出：

```
mysql> SHOW VARIABLES LIKE 'log_bin';
+---------------+-------+
| Variable_name | Value |
+---------------+-------+
| log_bin       | ON    |
+---------------+-------+

mysql> SHOW BINARY LOGS;
+------------------+-----------+
| Log_name         | File_size |
+------------------+-----------+
| mysql-bin.000001 |       154 |
| mysql-bin.000002 |       178 |
+------------------+-----------+

mysql> SHOW MASTER STATUS;
+------------------+----------+--------------+------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB |
+------------------+----------+--------------+------------------+
| mysql-bin.000002 |      178 |              |                  |
+------------------+----------+--------------+------------------+
```

### 方法二：直接查看文件

```bash
ls -lh /var/lib/mysql/mysql-bin.*
```

---

## 五、查看 binlog 内容

```bash
# 使用 mysqlbinlog 工具
mysqlbinlog /var/lib/mysql/mysql-bin.000001 | less

# 指定时间范围查看
mysqlbinlog --start-datetime="2025-01-01 00:00:00" \
            --stop-datetime="2025-01-02 00:00:00" \
            /var/lib/mysql/mysql-bin.000001

# 指定位置范围
mysqlbinlog --start-position=154 --stop-position=1024 \
            /var/lib/mysql/mysql-bin.000001
```

---

## 六、基于 binlog 恢复数据（简要）

```bash
# 1. 先用最近的全量备份恢复到某个时间点
mysql -u root -p < full_backup.sql

# 2. 再用 binlog 重放全量备份之后的操作
mysqlbinlog --start-datetime="2025-01-01 10:00:00" \
            --stop-datetime="2025-01-01 14:30:00" \
            /var/lib/mysql/mysql-bin.000005 | mysql -u root -p
```

---

## 七、手动管理 binlog

```sql
-- 清理 3 天前的 binlog
PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 3 DAY);

-- 清理到指定文件（保留该文件之后的）
PURGE BINARY LOGS TO 'mysql-bin.000010';

-- 重置所有 binlog（谨慎！会删除全部 binlog）
RESET MASTER;
```

---

## 八、三种 binlog 格式对比

| 格式 | 记录内容 | 优点 | 缺点 |
|---|---|---|---|
| **STATEMENT** | SQL 语句原文 | 文件小 | 非确定性函数（`NOW()`、`UUID()`）可能导致主从不一致 |
| **ROW** | 每行数据变更前后的值 | 数据一致性最好，主从最安全 | 文件较大 |
| **MIXED** | 默认用 STATEMENT，不安全时自动切 ROW | 折中方案 | 复杂场景仍可能出问题 |

> **生产环境强烈推荐 `ROW` 格式**，配合 `sync_binlog = 1` 和 InnoDB 的 `innodb_flush_log_at_trx_commit = 1` 可实现"双1"配置，保证数据安全。
