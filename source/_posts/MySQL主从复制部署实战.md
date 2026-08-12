---
title: MySQL 主从复制部署实战
date: 2026-08-14 09:30:00
tags:
  - MySQL
  - 主从
categories:
  - MySQL SRE
---

主从复制是 MySQL HA 与读写分离的基础。

## 主库配置（my.cnf）

```ini
[mysqld]
server-id = 1
log_bin = mysql-bin
binlog_format = ROW
gtid_mode = ON
enforce_gtid_consistency = ON
sync_binlog = 1
innodb_flush_log_at_trx_commit = 1

character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

## 创建复制账号

```sql
CREATE USER 'repl'@'%' IDENTIFIED BY 'repl_password';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
```

## 从库配置

```ini
[mysqld]
server-id = 2
read_only = ON
super_read_only = ON
gtid_mode = ON
enforce_gtid_consistency = ON
relay_log_recovery = ON
```

## 建立复制（GTID）

```sql
CHANGE MASTER TO
  MASTER_HOST='10.0.1.10',
  MASTER_USER='repl',
  MASTER_PASSWORD='repl_password',
  MASTER_AUTO_POSITION=1;
START SLAVE;
SHOW SLAVE STATUS\G
```

关注：`Slave_IO_Running: Yes`、`Slave_SQL_Running: Yes`、`Seconds_Behind_Master`。

## 部署检查清单

- [ ] server-id 全局唯一
- [ ] ROW 格式 binlog（避免语句模式数据不一致）
- [ ] GTID 开启便于 failover
- [ ] 从库 read_only
- [ ] 监控复制延迟与 SQL 线程错误

## 延迟排查

- 大事务、DDL 阻塞 SQL 线程
- 从库硬件弱于主库
- 并行复制未开：`slave_parallel_workers = 4`

主从本身不自动切换，需 Orchestrator / MHA / 人工。
