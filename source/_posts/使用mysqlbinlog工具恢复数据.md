---
title: 使用 mysqlbinlog 工具恢复数据
date: 2026-09-07 22:45:00
tags:
  - MySQL
  - binlog
  - 数据恢复
  - DBA
categories:
  - MySQL
---

## 一、概述

`mysqlbinlog` 是 MySQL 自带的一个实用工具，用于解析和读取二进制日志（binary log）。二进制日志记录了所有对数据库执行更改的操作（INSERT、UPDATE、DELETE 等），因此可以利用它来：

- **误操作恢复**：误删除、误更新数据后，回退到操作前的状态
- **基于时间点恢复（PITR）**：将数据库恢复到某个精确的时间点
- **主从复制**：在主从架构中，从库通过读取主库的 binlog 进行数据同步

---

## 二、前置条件

### 1. 确认 binlog 已开启

```sql
SHOW VARIABLES LIKE 'log_bin';
-- 结果应为 ON
```

### 2. 查看 binlog 相关配置

```sql
SHOW VARIABLES LIKE '%binlog%';
```

关键参数说明：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `log_bin` | 是否开启 binlog | ON |
| `binlog_format` | 日志格式 | ROW（推荐） |
| `binlog_expire_logs_seconds` | binlog 过期时间 | 根据需要设置 |
| `max_binlog_size` | 单个 binlog 文件最大大小 | 100M~1G |
| `server_id` | 服务器唯一标识 | 非零值 |

### 3. 在 my.cnf 中配置（如未开启）

```ini
[mysqld]
server-id        = 1
log_bin          = /var/lib/mysql/mysql-bin
binlog_format    = ROW
expire_logs_days = 7
max_binlog_size  = 500M
```

修改后重启 MySQL：

```bash
systemctl restart mysqld
```

---

## 三、查看 binlog 文件

### 1. 列出所有 binlog 文件

```sql
SHOW BINARY LOGS;
-- 或
SHOW MASTER LOGS;
```

输出示例：
```
+------------------+-----------+
| Log_name         | File_size |
+------------------+-----------+
| mysql-bin.000001 |    1048576|
| mysql-bin.000002 |    2097152|
| mysql-bin.000003 |     524288|
+------------------+-----------+
```

### 2. 查看当前正在使用的 binlog

```sql
SHOW MASTER STATUS;
```

---

## 四、mysqlbinlog 常用命令

### 1. 基本读取

```bash
# 读取单个 binlog 文件
mysqlbinlog mysql-bin.000003

# 读取多个 binlog 文件
mysqlbinlog mysql-bin.000001 mysql-bin.000002 mysql-bin.000003
```

### 2. 按时间范围筛选

```bash
mysqlbinlog \
  --start-datetime="2026-08-19 10:00:00" \
  --stop-datetime="2026-08-19 11:00:00" \
  mysql-bin.000003
```

### 3. 按位置（position）筛选

```bash
mysqlbinlog \
  --start-position=154 \
  --stop-position=1024 \
  mysql-bin.000003
```

### 4. 常用选项汇总

| 选项 | 说明 |
|------|------|
| `--start-datetime` | 起始时间 |
| `--stop-datetime` | 结束时间 |
| `--start-position` | 起始位置 |
| `--stop-position` | 结束位置 |
| `--database=db_name` | 只显示指定数据库的操作 |
| `--no-defaults` | 不读取默认配置文件 |
| `--base64-output=DECODE-ROWS` | 解码 ROW 格式为可读内容 |
| `-v` 或 `--verbose` | 将行事件重构为伪 SQL 语句 |
| `--skip-gtids` | 跳过 GTID（用于 GTID 复制场景） |

---

## 五、实战：数据恢复流程

### 场景描述

> 2026-08-19 10:30:00，某员工误执行了 `DELETE FROM orders WHERE status = 'pending'`，导致大量待处理订单被删除。需要恢复这些数据。

---

### 步骤 1：确认误操作所在的 binlog 文件

```sql
SHOW BINARY LOGS;
```

根据时间判断，误操作应该记录在 `mysql-bin.000005` 中。

### 步骤 2：定位误操作的精确位置

```bash
mysqlbinlog \
  --start-datetime="2026-08-19 10:25:00" \
  --stop-datetime="2026-08-19 10:35:00" \
  -v --base64-output=DECODE-ROWS \
  mysql-bin.000005
```

输出中查找误操作的 DELETE 语句，记录关键信息：

```
# at 7856                         <-- 误操作的起始 position
#260819 10:30:05 server id 1  end_log_pos 8130
DELETE FROM `test`.`orders` WHERE ...
```

假设误操作：
- **起始 position**：7856
- **结束 position**：8130
- **误操作时间**：10:30:05

### 步骤 3：确认恢复方案

有两种主流恢复方案：

#### 方案 A：利用 binlog 生成反向 SQL（推荐）

如果 binlog 格式为 `ROW`，可以提取误操作**之前**的行数据镜像（before image），从而重构 INSERT 语句来恢复数据。

```bash
mysqlbinlog \
  --start-position=154 \
  --stop-position=7856 \
  -v --base64-output=DECODE-ROWS \
  mysql-bin.000005 \
  > /tmp/before_delete.sql
```

> **注意**：MySQL 原生 mysqlbinlog 的 `-v` 选项在 ROW 格式下会显示删除前行的数据，但不会自动生成反向 INSERT 语句。通常需要借助第三方工具或手动处理。

#### 方案 B：截取误操作之前的 binlog 并重放

**思路**：先备份当前数据（防止二次误操作），然后将误操作之前的所有操作重放到一份空库或临时库中，再把丢失的数据导回来。

```bash
# 1) 先备份当前数据库
mysqldump -u root -p --single-transaction test > /tmp/test_current_backup.sql

# 2) 提取从库初始化（或全量备份点）到误操作之前的全部 binlog
mysqlbinlog \
  --start-datetime="2026-08-18 00:00:00" \
  --stop-position=7856 \
  mysql-bin.000004 mysql-bin.000005 \
  > /tmp/recover.sql

# 3) 在临时库中重放
mysql -u root -p -e "CREATE DATABASE test_recover;"
mysql -u root -p test_recover < /tmp/full_backup_before.sql   # 先恢复全量备份
mysql -u root -p test_recover < /tmp/recover.sql              # 再重放 binlog
```

#### 方案 C：跳过误操作继续重放后续 binlog（适用于整库恢复场景）

```bash
# 重放所有 binlog，但跳过误操作那段 (7856 ~ 8130)
mysqlbinlog \
  --start-datetime="2026-08-18 00:00:00" \
  --stop-position=7856 \
  mysql-bin.000004 mysql-bin.000005 \
  > /tmp/part1.sql

mysqlbinlog \
  --start-position=8130 \
  mysql-bin.000005 \
  > /tmp/part2.sql

mysql -u root -p test < /tmp/part1.sql
mysql -u root -p test < /tmp/part2.sql
```

---

## 六、使用 mysqlbinlog + 管道直接恢复

```bash
# 直接管道到 mysql 执行
mysqlbinlog \
  --start-position=154 \
  --stop-position=7856 \
  mysql-bin.000005 | mysql -u root -p

# 如果指定了数据库
mysqlbinlog \
  --database=test \
  --start-datetime="2026-08-19 10:00:00" \
  --stop-datetime="2026-08-19 10:30:00" \
  mysql-bin.000005 | mysql -u root -p
```

---

## 七、进阶：借助 binlog2sql 工具生成反向 SQL

由于原生 mysqlbinlog 对 ROW 格式的反向 SQL 支持有限，推荐使用开源工具 **binlog2sql**：

```bash
# 安装
pip install binlog2sql

# 生成误操作的反向 SQL（从 DELETE 变为 INSERT）
python binlog2sql.py \
  -h 127.0.0.1 -P 3306 -u root -p'password' \
  -d test -t orders \
  --start-file='mysql-bin.000005' \
  --start-pos=154 \
  --stop-pos=7856 \
  --sql-type=DELETE \
  --flashback \
  > /tmp/rollback.sql

# 审核后执行恢复
mysql -u root -p test < /tmp/rollback.sql
```

`--flashback` 参数会将 DELETE 的 before image 生成为对应的 INSERT 语句。

---

## 八、注意事项

1. **binlog 格式强烈推荐 ROW**
   - STATEMENT 格式只记录 SQL 语句本身，无法提取行级数据镜像
   - ROW 格式记录了每行数据变更前后的值，恢复精度更高

2. **及时保存 binlog**
   - binlog 有自动过期清理机制，误操作后第一时间确保相关 binlog 不被清理：
   ```sql
   SET GLOBAL expire_logs_days = 30;  -- 临时延长保留期
   ```

3. **恢复前先备份**
   - 在做任何恢复操作前，先用 `mysqldump` 备份当前状态

4. **先在测试环境验证**
   - 在临时库中验证恢复 SQL 的正确性，确认无误后再在生产库执行

5. **GTID 模式注意事项**
   - 如果开启了 GTID，在重放 binlog 时需要加 `--skip-gtids`，否则会因 GTID 冲突而跳过已执行的事务

6. **binlog 存储位置**
   ```bash
   # 查看 binlog 文件路径
   find / -name "mysql-bin.*" 2>/dev/null
   # 或查看配置
   SHOW VARIABLES LIKE 'log_bin_basename';
   ```

---

## 九、总结对比

| 方案 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| mysqlbinlog + 截取重放 | 整库/大批量恢复 | 原生工具，无需额外安装 | 需手动定位 position |
| mysqlbinlog + --stop-position 跳过误操作 | PITR 精确恢复 | 精确到 position 级别 | 操作复杂，需理解 binlog 结构 |
| binlog2sql --flashback | 单表/单语句反向恢复 | 自动生成反向 SQL，可审核 | 需要额外安装 Python 工具 |
| 全量备份 + binlog 增量恢复 | 灾难恢复 | 最完整的恢复链路 | 依赖全量备份的时效性 |

**最佳实践**：定期全量备份（mysqldump / xtrabackup）+ binlog 增量保留，两者结合是数据安全的基础保障。
