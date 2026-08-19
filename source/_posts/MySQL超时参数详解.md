---
title: MySQL 超时参数详解
date: 2026-09-08 06:30:00
tags:
  - MySQL
  - 参数调优
  - 超时
  - DBA
categories:
  - MySQL
---

MySQL 中有多个超时相关参数，作用于连接、查询、事务等不同层面。

---

## 一、连接层超时

| 参数 | 默认值 | 说明 |
|---|---|---|
| `connect_timeout` | 10s | 建立连接时的握手超时（认证阶段） |
| `wait_timeout` | 28800s (8h) | 非交互连接的空闲超时 |
| `interactive_timeout` | 28800s (8h) | 交互连接（如 mysql CLI）的空闲超时 |
| `net_read_timeout` | 30s | 等待从连接读取数据的超时 |
| `net_write_timeout` | 60s | 等待向连接写入数据的超时 |
| `max_connect_errors` | 100 | 连接错误累计超过此值后封锁主机 |

```sql
-- 查看当前值
SHOW VARIABLES LIKE '%timeout%';
SHOW VARIABLES LIKE '%connect%';
```

---

## 二、查询/语句层超时

| 参数 | 默认值 | 说明 |
|---|---|---|
| `wait_timeout` | 28800s | 连接空闲超时（同上） |
| `max_execution_time` | 0 (不限) | SELECT 语句最大执行时间（毫秒），MySQL 5.7.8+ |
| `lock_wait_timeout` | 31536000s (1年) | DDL 语句等待元数据锁的超时 |
| `innodb_lock_wait_timeout` | 50s | InnoDB 行锁等待超时 |
| `innodb_rollback_on_timeout` | OFF | 锁等待超时时是否回滚整个事务 |

```sql
-- 设置单条 SELECT 的超时（毫秒）
SET max_execution_time = 5000;

-- 设置 InnoDB 行锁等待超时
SET GLOBAL innodb_lock_wait_timeout = 30;
```

---

## 三、复制相关超时

| 参数 | 默认值 | 说明 |
|---|---|---|
| `slave_net_timeout` | 60s | 从库判断主库连接断开的心跳超时 |
| `master_connect_retry` | 60s | 从库重连主库的间隔 |
| `rpl_semi_sync_master_timeout` | 10000ms | 半同步复制降级为异步的等待超时 |

---

## 四、重要参数详解

### 1. `wait_timeout` vs `interactive_timeout`

```
客户端连接类型判断:
├── 交互式连接 (CLIENT_INTERACTIVE 标志)
│   → 使用 interactive_timeout
│   → 例如: mysql 命令行客户端
└── 非交互式连接
    → 使用 wait_timeout
    → 例如: JDBC、Python 连接池
```

### 2. `innodb_lock_wait_timeout`

```sql
-- 场景: 事务等待行锁超过 50s 默认值
-- 表现: ERROR 1205 (HY000): Lock wait timeout exceeded

-- 查看当前锁等待
SELECT * FROM information_schema.INNODB_TRX;
SELECT * FROM sys.innodb_lock_waits;

-- 临时调大（session 级别）
SET SESSION innodb_lock_wait_timeout = 120;
```

### 3. `max_execution_time`（查询超时杀查询）

```sql
-- 全局设置：所有 SELECT 最长执行 10 秒
SET GLOBAL max_execution_time = 10000;

-- 单条语句hint
SELECT /*+ MAX_EXECUTION_TIME(5000) */ * FROM huge_table WHERE ...;
```

---

## 五、客户端侧超时参数

除了服务端，**客户端驱动**也有自己的超时设置：

| 驱动 | 参数 | 说明 |
|---|---|---|
| JDBC | `connectTimeout` | 建连超时 (ms) |
| JDBC | `socketTimeout` | 读取超时 (ms) |
| Python (PyMySQL) | `connect_timeout` | 建连超时 (s) |
| Python (PyMySQL) | `read_timeout` / `write_timeout` | 读写超时 (s) |
| Go (go-sql-driver) | `timeout` | 建连超时 |
| Go (go-sql-driver) | `readTimeout` / `writeTimeout` | 读写超时 |

**原则**：客户端超时应 <= 服务端超时，否则服务端会保持无效连接。

---

## 六、生产环境推荐配置参考

```ini
[mysqld]
# 连接层
connect_timeout                = 10
wait_timeout                   = 600        # 非交互 10 分钟
interactive_timeout            = 1800       # 交互 30 分钟
net_read_timeout               = 30
net_write_timeout              = 60

# InnoDB 锁
innodb_lock_wait_timeout       = 10         # 缩短到 10s，快速失败
innodb_rollback_on_timeout     = ON

# 查询超时（按需开启）
max_execution_time             = 30000      # 30 秒

# 复制
slave_net_timeout              = 10         # 心跳缩短，快速感知断连
```

---

**核心原则**：根据应用实际需求缩短超时，快速释放无效资源，避免连接池耗尽或锁堆积。如果你有具体的场景（比如频繁出现 Lock wait timeout 或 Too many connections），可以进一步分析。
