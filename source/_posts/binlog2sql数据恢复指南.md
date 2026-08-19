---
title: binlog2sql 数据恢复指南
date: 2026-09-08 03:00:00
tags:
  - MySQL
  - binlog2sql
  - 数据恢复
  - DBA
categories:
  - MySQL
---

## 简介

`binlog2sql` 是大众点评开源的一个工具，可以从 MySQL 的 binlog 中解析出原始 SQL，也可以生成**反向 SQL（回滚SQL）**，从而实现数据恢复。

GitHub 地址：`https://github.com/danfengcao/binlog2sql`

---

## 一、环境准备

### 1. 安装依赖

```bash
# Python 2.7, 3.4+
pip install mysql-replication
pip install pyquery
```

### 2. 克隆工具

```bash
git clone https://github.com/danfengcao/binlog2sql.git
cd binlog2sql
```

### 3. MySQL 配置要求

```ini
# my.cnf
[mysqld]
server_id = 1
log_bin = /var/log/mysql/mysql-bin.log
binlog_format = ROW          # 必须是 ROW 格式
binlog_row_image = FULL      # 必须是 FULL，记录完整的行数据
```

验证配置：

```sql
SHOW VARIABLES LIKE 'binlog_format';
SHOW VARIABLES LIKE 'binlog_row_image';
SHOW VARIABLES LIKE 'server_id';
```

---

## 二、权限要求

```sql
-- 需要的最小权限
GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'recovery_user'@'%';
```

---

## 三、核心用法

### 1. 查看 binlog 列表

```sql
SHOW BINARY LOGS;
SHOW MASTER STATUS;  -- 当前正在写入的 binlog
```

### 2. 解析原始 SQL（查看执行了什么）

```bash
python binlog2sql.py \
  -h 127.0.0.1 \
  -P 3306 \
  -u root \
  -p 'password' \
  -d 数据库名 \
  -t 表名 \
  --start-file='mysql-bin.000005' \
  --start-datetime='2025-01-15 10:00:00' \
  --stop-datetime='2025-01-15 12:00:00'
```

### 3. 生成回滚 SQL（恢复数据的关键）

```bash
python binlog2sql.py \
  -h 127.0.0.1 \
  -P 3306 \
  -u root \
  -p 'password' \
  -d 数据库名 \
  -t 表名 \
  --start-file='mysql-bin.000005' \
  --start-position=154 \
  --stop-position=12032 \
  -B > rollback.sql
```

> **`-B` 参数是关键** — 它会将 DELETE、UPDATE、INSERT 自动生成对应的反向 SQL。

---

## 四、恢复场景详解

### 场景 1：误删 DELETE 数据恢复

假设有人在 14:30 执行了误删：

```bash
# 第一步：找到误删操作的 binlog 位置
python binlog2sql.py \
  -h 127.0.0.1 -u root -p 'password' \
  -d mydb -t mytable \
  --start-file='mysql-bin.000008' \
  --start-datetime='2025-01-15 14:00:00' \
  --stop-datetime='2025-01-15 15:00:00'

# 输出示例：
# DELETE FROM `mydb`.`mytable` WHERE `id`=1 AND `name`='张三'; ...
# DELETE FROM `mydb`.`mytable` WHERE `id`=2 AND `name`='李四'; ...
# -- at position: 8932
```

```bash
# 第二步：生成回滚 SQL
python binlog2sql.py \
  -h 127.0.0.1 -u root -p 'password' \
  -d mydb -t mytable \
  --start-file='mysql-bin.000008' \
  --start-position=8932 \
  --stop-position=9500 \
  -B > rollback.sql
```

```bash
# 第三步：检查并执行回滚
cat rollback.sql
# INSERT INTO `mydb`.`mytable`(`id`, `name`) VALUES (2, '李四');
# INSERT INTO `mydb`.`mytable`(`id`, `name`) VALUES (1, '张三');

mysql -u root -p mydb < rollback.sql
```

### 场景 2：误改 UPDATE 数据恢复

```bash
# binlog2sql 解析出的原始 SQL：
# UPDATE `mydb`.`user` SET `status`=0 WHERE `id`=100 LIMIT 100;

# 加 -B 后生成的回滚 SQL：
# UPDATE `mydb`.`user` SET `status`=1 WHERE `id`=100 LIMIT 100;
```

### 场景 3：误插入 INSERT 恢复

```bash
# 加 -B 后 DELETE 变为 INSERT，INSERT 变为 DELETE
# 原始：INSERT INTO `t` VALUES (1,'test');
# 回滚：DELETE FROM `t` WHERE `id`=1 AND `name`='test' LIMIT 1;
```

---

## 五、参数速查

| 参数 | 说明 |
|---|---|
| `-h` | MySQL 主机地址 |
| `-P` | 端口号 |
| `-u` | 用户名 |
| `-p` | 密码 |
| `-d` | 数据库名 |
| `-t` | 表名（可多个 `-t t1 -t t2`） |
| `--start-file` | 起始 binlog 文件 |
| `--stop-file` | 结束 binlog 文件 |
| `--start-position` | 起始位置（精确） |
| `--stop-position` | 结束位置（精确） |
| `--start-datetime` | 起始时间 |
| `--stop-datetime` | 结束时间 |
| `-B` / `--flashback` | **生成回滚SQL（核心参数）** |
| `--no-primary-key` | 对 INSERT 语句不带 PK 的表做特殊处理 |
| `-K` / `--no-primary-key` | INSERT 的回滚不带 WHERE 主键条件 |

---

## 六、注意事项

### 能恢复的情况

- binlog 格式为 **ROW** 且 `binlog_row_image = FULL`
- 误操作的 binlog 文件**尚未被清理**（未过期或手动 `PURGE`）
- 表结构没有发生 DDL 变更（加列、删列等会影响回滚）

### 无法恢复的情况

| 情况 | 原因 |
|---|---|
| binlog 已被清理 | `expire_logs_days` 到期或 `PURGE BINARY LOGS` |
| `binlog_format = STATEMENT/MIXED` | 行数据未记录在 binlog 中 |
| `binlog_row_image = MINIMAL` | 只记录变更列，回滚信息不完整 |
| DDL 操作（DROP TABLE、ALTER TABLE） | DDL 不记录行数据，无法用此工具回滚 |
| binlog 已被 `RESET MASTER` 清除 | 数据永久丢失 |

### 安全建议

```bash
# 1. 恢复前先备份当前数据
mysqldump -u root -p mydb mytable > backup_before_rollback.sql

# 2. 先用不带 -B 的命令确认影响范围
python binlog2sql.py ... --start-position=X --stop-position=Y

# 3. 审查回滚 SQL 内容无误后再执行
cat rollback.sql

# 4. 建议在测试环境先验证
```

---

## 七、替代工具对比

| 工具 | 特点 |
|---|---|
| **binlog2sql** | 轻量、纯 Python、flashback 回滚 |
| **mysqlbinlog** | 官方自带、解析 binlog 为文本 SQL |
| **MyFlash** | 美团开源、C 语言、性能更好，支持 flashback |
| **binlog-rollback** | 另一个开源回滚工具 |

---

## 快速恢复流程总结

```
误操作发生
    │
    ▼
确认误操作时间范围 / binlog 文件
    │
    ▼
binlog2sql 定位误操作的 position
    │
    ▼
binlog2sql -B 生成回滚 SQL
    │
    ▼
审查回滚 SQL（确认逻辑正确）
    │
    ▼
备份当前表数据
    │
    ▼
执行回滚 SQL
    │
    ▼
验证数据恢复情况
```

如果你有具体的恢复场景，可以告诉我更多细节，我帮你构造精确的命令。
