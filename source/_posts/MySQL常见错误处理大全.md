---
title: MySQL 常见错误处理大全
date: 2026-09-08 05:15:00
tags:
  - MySQL
  - 故障排查
  - 错误处理
  - DBA
categories:
  - MySQL
---

---

## 一、连接类错误

### 1. ERROR 1045 (28000): Access denied for user

**报错场景：**
```
ERROR 1045 (28000): Access denied for user 'root'@'localhost' (using password: YES)
```

**原因：** 用户名或密码错误，或用户没有访问权限。

**解决：**

```sql
-- 1. 确认密码是否正确
mysql -u root -p

-- 2. 如果忘记 root 密码，重置密码
-- 停止 MySQL
systemctl stop mysqld

-- 跳过授权表启动
mysqld_safe --skip-grant-tables &

-- 无密码登录后修改
mysql -u root
ALTER USER 'root'@'localhost' IDENTIFIED BY '新密码';
FLUSH PRIVILEGES;

-- 3. 授权远程访问
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY '密码' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

---

### 2. ERROR 2003 (HY000): Can't connect to MySQL server

**报错场景：**
```
ERROR 2003 (HY000): Can't connect to MySQL server on '192.168.1.100' (111)
```

**原因：** 网络不通、MySQL 未启动、端口不对、防火墙拦截。

**排查流程：**

```bash
# 1. 检查 MySQL 是否运行
systemctl status mysqld

# 2. 检查监听端口
ss -tlnp | grep 3306
# 如果只监听 127.0.0.1，说明绑定了本地，需修改配置

# 3. 检查防火墙
firewall-cmd --list-ports
firewall-cmd --add-port=3306/tcp --permanent
firewall-cmd --reload

# 4. 检查 bind-address 配置
vim /etc/my.cnf
```

```ini
[mysqld]
bind-address = 0.0.0.0    # 允许所有 IP 连接
port = 3306
```

---

### 3. ERROR 1129 (HY000): Host is blocked

**报错场景：**
```
ERROR 1129 (HY000): Host '192.168.1.50' is blocked because of many connection errors
```

**原因：** 某主机连接失败次数过多，触发了 MySQL 的安全机制。

**解决：**

```sql
-- 方法一：清除主机缓存
FLUSH HOSTS;

-- 方法二：增大允许的错误次数
SET GLOBAL max_connect_errors = 100000;

-- 永久生效
-- my.cnf 中添加：
[mysqld]
max_connect_errors = 100000
```

---

### 4. ERROR 1040 (08004): Too many connections

**报错场景：**
```
ERROR 1040 (08004): Too many connections
```

**原因：** 连接数达到上限。

**解决：**

```sql
-- 查看当前连接数
SHOW STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';

-- 临时调大
SET GLOBAL max_connections = 500;

-- 查看哪些连接占用
SHOW PROCESSLIST;
-- 批量清理 Sleep 过久的连接
```

```ini
# 永久生效
[mysqld]
max_connections = 500
wait_timeout = 300
interactive_timeout = 300
```

---

### 5. ERROR 2006: MySQL server has gone away

**报错场景：**
```
ERROR 2006 (HY000): MySQL server has gone away
```

**原因：** 执行过程中连接断开，通常是数据包过大或超时。

**解决：**

```sql
-- 1. 增大数据包限制
SET GLOBAL max_allowed_packet = 256 * 1024 * 1024;

-- 2. 增大超时时间
SET GLOBAL wait_timeout = 28800;
SET GLOBAL interactive_timeout = 28800;
```

```ini
[mysqld]
max_allowed_packet = 256M
wait_timeout = 28800
```

---

## 二、SQL 语法与数据类错误

### 6. ERROR 1064 (42000): SQL syntax error

**报错场景：**
```
ERROR 1064 (42000): You have an error in your SQL syntax
```

**常见原因及修复：**

```sql
-- 1. 使用了 MySQL 保留字作为表名/字段名
-- 错误
SELECT order FROM table;
-- 正确：用反引号包裹
SELECT `order` FROM `table`;

-- 2. 字符串未用引号
-- 错误
SELECT * FROM users WHERE name = John;
-- 正确
SELECT * FROM users WHERE name = 'John';

-- 3. 缺少逗号或括号不匹配
-- 错误
INSERT INTO users (name age) VALUES ('Tom' 25);
-- 正确
INSERT INTO users (name, age) VALUES ('Tom', 25);

-- 4. MySQL 版本关键字差异
-- 8.0+ 中 USING 关键字行为有变化
```

---

### 7. ERROR 1054 (42S22): Unknown column

**报错场景：**
```
ERROR 1054 (42S22): Unknown column 'username' in 'field list'
```

**排查：**

```sql
-- 确认表结构
DESCRIBE users;
SHOW COLUMNS FROM users;

-- 常见原因：字段名拼写错误、大小写问题、别名错误
SELECT name AS username FROM users;
-- WHERE 中不能直接使用 SELECT 的别名（MySQL 5.x）
SELECT name AS username FROM users WHERE username = 'Tom';  -- 可能报错
SELECT name AS username FROM users WHERE name = 'Tom';      -- 正确
```

---

### 8. ERROR 1366: Incorrect string value

**报错场景：**
```
ERROR 1366 (HY000): Incorrect string value: '\xF0\x9F\x98\x80' for column 'content'
```

**原因：** 存储 emoji 或特殊字符时，字符集不支持。

**解决：**

```sql
-- 1. 查看当前字符集
SHOW VARIABLES LIKE 'character_set%';
SHOW VARIABLES LIKE 'collation%';

-- 2. 将库、表、字段改为 utf8mb4（支持 emoji）
ALTER DATABASE your_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE your_table CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 3. 连接时指定字符集
SET NAMES utf8mb4;
```

```ini
[mysqld]
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[client]
default-character-set = utf8mb4
```

---

### 9. ERROR 1292 (22007): Incorrect datetime value

**报错场景：**
```
ERROR 1292 (22007): Incorrect datetime value: '2025-13-01' for column 'created_at'
```

**解决：**

```sql
-- 检查数据格式
-- MySQL 严格模式下会拒绝非法日期
SHOW VARIABLES LIKE 'sql_mode';

-- 临时关闭严格模式（不推荐用于生产）
SET SESSION sql_mode = '';

-- 正确做法：修正数据
UPDATE orders SET created_at = '2025-12-01' WHERE id = 100;
```

---

### 10. ERROR 1062: Duplicate entry

**报错场景：**
```
ERROR 1062 (23000): Duplicate entry '1001' for key 'PRIMARY'
```

**解决：**

```sql
-- 方法一：忽略重复（跳过已存在的记录）
INSERT IGNORE INTO users (id, name) VALUES (1001, 'Tom');

-- 方法二：存在则更新（upsert）
INSERT INTO users (id, name, age)
VALUES (1001, 'Tom', 25)
ON DUPLICATE KEY UPDATE name = 'Tom', age = 25;

-- 方法三：查看冲突记录
SELECT * FROM users WHERE id = 1001;
```

---

## 三、表与索引类错误

### 11. ERROR 1146: Table doesn't exist

```
ERROR 1146 (42S02): Table 'db_name.table_name' doesn't exist
```

**排查：**

```sql
-- 1. 确认数据库
USE db_name;
SHOW TABLES;

-- 2. 大小写问题（Linux 文件系统区分大小写）
-- my.cnf 中设置
[mysqld]
lower_case_table_names = 1

-- 3. 表文件损坏
-- 检查 .frm 和 .ibd 文件是否存在于数据目录
ls /var/lib/mysql/db_name/
```

---

### 12. ERROR 1114: Table is full

```
ERROR 1114 (HY000): The table 'logs' is full
```

**原因：** 磁盘满或 InnoDB 表空间达到限制。

```sql
-- 1. 检查磁盘空间
df -h

-- 2. 检查表空间设置
SHOW VARIABLES LIKE 'innodb_data_file_path';
-- 可设为自动扩展
SET GLOBAL innodb_data_file_path = 'ibdata1:12M:autoextend';

-- 3. 清理数据
DELETE FROM logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
OPTIMIZE TABLE logs;
```

---

### 13. ERROR 1206: The total number of locks exceeds the lock table size

```
ERROR 1206 (HY000): The total number of locks exceeds the lock table size
```

**解决：**

```sql
-- 查看当前值
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';

-- 调大（通常设为物理内存的 60%-80%）
SET GLOBAL innodb_buffer_pool_size = 2 * 1024 * 1024 * 1024;  -- 2GB
```

```ini
[mysqld]
innodb_buffer_pool_size = 4G
```

---

## 四、InnoDB 存储引擎错误

### 14. ERROR 1213: Deadlock found

```
ERROR 1213 (40001): Deadlock found when trying to get lock
```

**排查：**

```sql
-- 1. 查看最近的死锁信息
SHOW ENGINE INNODB STATUS\G
-- 关注 LATEST DETECTED DEADLOCK 部分

-- 2. 开启死锁日志记录
SET GLOBAL innodb_print_all_deadlocks = ON;
```

**预防策略：**

```sql
-- 1. 事务尽量短小，快速提交
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;

-- 2. 按固定顺序访问表和行
-- 总是先操作 id 小的行

-- 3. 使用合理的索引，减少锁范围
-- 避免全表扫描导致的大范围行锁升级为表锁

-- 4. 降低隔离级别
SET SESSION transaction_isolation = 'READ-COMMITTED';
```

---

### 15. ERROR 1205: Lock wait timeout exceeded

```
ERROR 1205 (HY000): Lock wait timeout exceeded; try restarting transaction
```

**解决：**

```sql
-- 1. 查看当前锁等待
SELECT * FROM information_schema.INNODB_TRX;
SELECT * FROM sys.innodb_lock_waits;

-- 2. 查找持有锁的线程
SELECT
    r.trx_id AS waiting_trx,
    r.trx_mysql_thread_id AS waiting_thread,
    b.trx_id AS blocking_trx,
    b.trx_mysql_thread_id AS blocking_thread
FROM information_schema.INNODB_LOCK_WAITS w
JOIN information_schema.INNODB_TRX b ON w.blocking_trx_id = b.trx_id
JOIN information_schema.INNODB_TRX r ON w.requesting_trx_id = r.trx_id;

-- 3. 杀掉阻塞线程
KILL <blocking_thread_id>;

-- 4. 调整超时时间
SET GLOBAL innodb_lock_wait_timeout = 120;  -- 默认 50 秒
```

---

## 五、复制（Replication）类错误

### 16. Slave: Error in log event

```
ERROR 1594: Relay log read failure
```

**解决：**

```sql
-- 方法一：跳过错误
STOP SLAVE;
SET GLOBAL sql_slave_skip_counter = 1;
START SLAVE;

-- 方法二：重建从库
STOP SLAVE;
RESET SLAVE ALL;

-- 在主库重新导出
mysqldump --master-data=2 --single-transaction -A > full_backup.sql

-- 在从库导入后重新配置
CHANGE MASTER TO
    MASTER_HOST='192.168.1.100',
    MASTER_USER='repl',
    MASTER_PASSWORD='密码',
    MASTER_LOG_FILE='mysql-bin.000010',
    MASTER_LOG_POS=154;
START SLAVE;
```

---

### 17. Slave: Seconds_Behind_Master 不断增大

```sql
-- 查看从库状态
SHOW SLAVE STATUS\G

-- 关注字段：
-- Slave_IO_Running: Yes
-- Slave_SQL_Running: Yes
-- Seconds_Behind_Master: 0   ← 正常应接近 0
-- Last_Error / Last_SQL_Error

-- 优化方案：
-- 1. 从库开启并行复制
[mysqld]
slave_parallel_type = LOGICAL_CLOCK
slave_parallel_workers = 8

-- 2. 从库关闭不必要的日志
[mysqld]
skip-log-bin           -- 如果从库不需要级联复制
innodb_flush_log_at_trx_commit = 0
sync_binlog = 0
```

---

## 六、性能相关错误/警告

### 18. ERROR 1153: Got a packet bigger than 'max_allowed_packet'

```
Got a packet bigger than 'max_allowed_packet' bytes
```

```sql
-- 查看当前值
SHOW VARIABLES LIKE 'max_allowed_packet';

-- 设置为 256MB
SET GLOBAL max_allowed_packet = 268435456;
```

```ini
[mysqld]
max_allowed_packet = 256M

[client]
max_allowed_packet = 256M
```

---

### 19. Warning: Unsafe statement in binlog

```
Warning: Unsafe statement written to the binary log using statement format
```

**原因：** 使用了 `STATEMENT` 格式的 binlog，但 SQL 中包含不确定函数。

**解决：**

```ini
[mysqld]
binlog_format = ROW        # 推荐使用 ROW 格式
binlog_row_image = FULL
```

---

## 七、快速诊断工具速查表

| 排查方向 | 常用命令 |
|---|---|
| 查看连接状态 | `SHOW PROCESSLIST;` |
| 查看所有变量 | `SHOW GLOBAL VARIABLES;` |
| 查看服务器状态 | `SHOW GLOBAL STATUS;` |
| 查看表结构 | `DESC table_name;` |
| 查看索引 | `SHOW INDEX FROM table_name;` |
| 查看建表语句 | `SHOW CREATE TABLE table_name\G` |
| 查看 InnoDB 引擎状态 | `SHOW ENGINE INNODB STATUS\G` |
| 查看错误日志 | `SHOW VARIABLES LIKE 'log_error';` |
| 查看慢查询 | `SHOW VARIABLES LIKE 'slow_query%';` |
| 查看复制状态 | `SHOW SLAVE STATUS\G` |
| 查看锁等待 | `SELECT * FROM sys.innodb_lock_waits;` |
| 查看表空间 | `SELECT table_name, data_length/1024/1024 AS data_mb FROM information_schema.tables WHERE table_schema='db_name';` |

---

## 八、经验法则总结

```
遇到报错的一般处理流程：

  读错误日志
      │
      ├─ 连接类 → 检查网络/权限/最大连接数
      │
      ├─ 语法类 → 检查 SQL 拼写/版本差异/保留字
      │
      ├─ 数据类 → 检查字符集/数据格式/约束冲突
      │
      ├─ 锁相关 → 查看锁等待/死锁日志/事务粒度
      │
      ├─ 复制类 → 检查从库状态/binlog 一致性
      │
      └─ 资源类 → 检查磁盘/内存/超时参数
```

日常建议：**开启慢查询日志 + 错误日志 + 定期检查 `SHOW PROCESSLIST`**，大部分问题都能在爆发前被发现。
