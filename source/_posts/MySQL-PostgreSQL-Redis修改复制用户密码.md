---
title: MySQL PostgreSQL Redis修改复制用户密码
date: 2026-09-08 02:30:00
tags:
  - MySQL
  - PostgreSQL
  - Redis
  - 主从复制
  - DBA
categories:
  - 数据库
---

---

## 一、MySQL

### 1. 查看现有复制用户

```sql
SELECT user, host FROM mysql.user WHERE repl_slave_priv = 'Y';
-- 或者直接查看复制状态
SHOW SLAVE STATUS\G
```

### 2. 修改复制用户密码

```sql
-- 方法一：ALTER USER（MySQL 5.7+）
ALTER USER 'repl'@'%' IDENTIFIED BY 'NewPassword@2024';

-- 方法二：SET PASSWORD
SET PASSWORD FOR 'repl'@'%' = 'NewPassword@2024';

-- 方法三：GRANT（同时重置密码和权限）
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%' IDENTIFIED BY 'NewPassword@2024';

-- 刷新权限
FLUSH PRIVILEGES;
```

### 3. 从库端更新密码并重启复制

```sql
-- 停止复制
STOP SLAVE;

-- 更新主库认证信息
CHANGE MASTER TO
  MASTER_USER='repl',
  MASTER_PASSWORD='NewPassword@2024';

-- 如果是 MySQL 8.0.23+，使用新语法
CHANGE REPLICATION SOURCE TO
  SOURCE_USER='repl',
  SOURCE_PASSWORD='NewPassword@2024';

-- 重新启动复制
START SLAVE;

-- 验证
SHOW SLAVE STATUS\G
-- 确认 Slave_IO_Running: Yes, Slave_SQL_Running: Yes
```

---

## 二、PostgreSQL

### 1. 原理说明

PostgreSQL 的复制认证通过 **`pg_hba.conf`** 中的规则控制，密码存储在 **`pg_shadow`** 系统表中。

### 2. 修改复制用户密码

```sql
-- 在主库上执行
ALTER USER replicator WITH PASSWORD 'NewPassword@2024';
```

### 3. 确认 `pg_hba.conf` 配置

```bash
# 编辑 pg_hba.conf
vim /path/to/data/pg_hba.conf
```

```conf
# 确保复制连接使用 md5 或 scram-sha-256 认证
host    replication    replicator    192.168.1.0/24    md5
```

### 4. 重载配置

```sql
-- 不需要重启，只需重载
SELECT pg_reload_conf();
-- 或在命令行
pg_ctl reload -D /path/to/data
```

### 5. 从库端更新密码

**方式一：`standby.signal` + `postgresql.auto.conf`（PostgreSQL 12+）**

```bash
# 编辑密码文件（推荐使用 .pgpass）
vim ~/.pgpass
```

```
# 格式：主机:端口:数据库:用户名:密码
192.168.1.100:5432:replication:replicator:NewPassword@2024
```

```bash
# 设置权限
chmod 600 ~/.pgpass

# 重启从库
pg_ctl restart -D /path/to/data
```

**方式二：修改连接串（旧版本）**

```bash
# 在从库的 postgresql.conf 或 recovery.conf 中
primary_conninfo = 'host=192.168.1.100 port=5432 user=replicator password=NewPassword@2024'
```

### 6. 验证复制状态

```sql
-- 主库
SELECT * FROM pg_stat_replication;

-- 从库
SELECT * FROM pg_stat_wal_receiver;
```

---

## 三、Redis

### 1. 原理说明

Redis 复制认证有两种方式：
- **`requirepass`**：Redis 6.0 之前通用
- **`masteruser` + `masterauth`**：Redis 6.0+ 支持 ACL 用户

### 2. 修改密码

**Redis 6.0 之前（单密码模式）**

```bash
# 在主节点上修改密码
redis-cli -a OldPassword
CONFIG SET requirepass "NewPassword@2024"
```

**Redis 6.0+ （ACL 模式，推荐）**

```bash
# 创建专用复制用户
ACL SETUSER repl-user on >NewPassword@2024 +psync +replconf +ping

# 设置为默认用户（可选）
ACL SETUSER repl-user on >NewPassword@2024 ~* &* +@all
```

### 3. 从节点更新密码

**修改配置文件 `redis.conf`**

```bash
vim /etc/redis/redis.conf
```

```conf
# Redis 6.0 之前
masterauth NewPassword@2024

# Redis 6.0+ ACL 模式
masteruser repl-user
masterauth NewPassword@2024
```

**或通过运行时命令（不停服务）**

```bash
# 连接到从节点
redis-cli

# 动态更新
CONFIG SET masterauth "NewPassword@2024"

# Redis 6.0+ 还需设置用户
CONFIG SET masteruser "repl-user"
```

### 4. 验证复制状态

```bash
# 从节点
redis-cli INFO replication
# 确认 role:slave, master_link_status:up

# 主节点
redis-cli INFO replication
# 确认 connected_slaves 数量
```

---

## 总结对比

| 项目 | MySQL | PostgreSQL | Redis |
|---|---|---|---|
| 修改密码命令 | `ALTER USER` | `ALTER USER` | `ACL SETUSER` / `CONFIG SET requirepass` |
| 是否需要重启复制 | **需要**（`CHANGE MASTER TO`） | **需要**重启从库或重载 | **不需要**（`CONFIG SET` 即时生效） |
| 配置文件变更 | 无需 | 可能需要 `.pgpass` | 需要同步修改 `redis.conf` |
| 认证方式 | 用户+密码 | `pg_hba.conf` + 密码 | 单密码/ACL |
| 生产建议 | 修改前先确认从库连接状态 | 优先用 `.pgpass` 管理密码 | Redis 6.0+ 优先使用 ACL |

> **生产环境建议**：修改密码前先确认主从复制状态正常，修改后立即验证复制是否恢复，避免长时间中断导致数据不一致。
