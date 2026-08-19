---
title: MySQL优化与常用问题定位
date: 2026-09-08 01:00:00
tags:
  - MySQL
  - 慢查询
  - 性能优化
  - DBA
categories:
  - MySQL
---

---

## 一、慢查询定位

### 1. 开启慢查询日志

```sql
-- 查看当前配置
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- 动态开启
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;          -- 超过1秒记录
SET GLOBAL log_queries_not_using_indexes = ON;  -- 记录未使用索引的查询

-- 永久生效写入 my.cnf
-- [mysqld]
-- slow_query_log = 1
-- slow_query_log_file = /var/log/mysql/slow.log
-- long_query_time = 1
```

### 2. 分析慢查询日志

```bash
# mysqldumpslow 工具（MySQL 自带）
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log   # 按时间排序取 Top 10
mysqldumpslow -s c -t 10 /var/log/mysql/slow.log   # 按次数排序

# pt-query-digest（Percona Toolkit，更强大）
pt-query-digest /var/log/mysql/slow.log > report.txt
```

---

## 二、EXPLAIN 执行计划分析

这是优化查询的**核心工具**：

```sql
EXPLAIN SELECT * FROM orders WHERE user_id = 100 AND status = 'paid';
```

### 关键字段解读

| 字段 | 含义 | 关注点 |
|------|------|--------|
| **type** | 访问类型 | 从好到差：`system > const > eq_ref > ref > range > index > ALL` |
| **key** | 实际使用的索引 | NULL 表示没有使用索引 |
| **rows** | 预估扫描行数 | 越小越好 |
| **Extra** | 额外信息 | 关注 `Using filesort`、`Using temporary`、`Using index` |
| **filtered** | 过滤比例 | 百分比越高越好 |
| **possible_keys** | 可能用到的索引 | 与实际 key 对比，判断索引选择是否合理 |

### Extra 常见值含义

```
Using index          -- 覆盖索引，理想情况 ✓
Using where          -- 在存储引擎层过滤后，Server 层还需再次过滤
Using filesort       -- 需要额外排序操作，通常需要优化 ✗
Using temporary      -- 使用了临时表，通常需要优化 ✗
Using index condition -- 索引下推（ICP），MySQL 5.6+，是好事 ✓
```

### EXPLAIN FORMAT=JSON（更详细）

```sql
EXPLAIN FORMAT=JSON SELECT * FROM orders WHERE user_id = 100\G
```

可以得到实际的cost估算、扫描行数等精确信息。

---

## 三、索引优化

### 1. 索引失效的常见场景

```sql
-- ❌ 对索引列使用函数或运算
SELECT * FROM users WHERE YEAR(created_at) = 2024;
-- ✅ 改为范围查询
SELECT * FROM users WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';

-- ❌ 隐式类型转换
SELECT * FROM orders WHERE order_no = 12345;  -- order_no 是 varchar
-- ✅ 类型一致
SELECT * FROM orders WHERE order_no = '12345';

-- ❌ LIKE 以通配符开头
SELECT * FROM users WHERE name LIKE '%张';
-- ✅ 前缀匹配可以用索引
SELECT * FROM users WHERE name LIKE '张%';

-- ❌ OR 连接的条件中有非索引列
SELECT * FROM users WHERE indexed_col = 1 OR non_indexed_col = 2;
-- ✅ 确保 OR 两侧都有索引，或改用 UNION

-- ❌ NOT IN / NOT EXISTS / != / <> 可能导致全表扫描
-- 取决于数据分布，需用 EXPLAIN 验证

-- ❌ 最左前缀原则违反
-- 联合索引 idx(a, b, c)
SELECT * FROM t WHERE b = 1 AND c = 2;  -- 跳过了 a，索引失效
```

### 2. 索引设计原则

```
┌──────────────────────────────────────────────────────────┐
│                  索引设计四字口诀                          │
│                                                          │
│  等值放前, 范围放后                                       │
│  频繁查询, 优先覆盖                                       │
│  区分度高, 放联合前                                       │
│  排序分组, 借助索引                                       │
└──────────────────────────────────────────────────────────┘
```

```sql
-- 高区分度的列放前面
-- 假设 user_id 区分度 > status 区分度
ALTER TABLE orders ADD INDEX idx_user_status (user_id, status);

-- 覆盖索引：查询字段全在索引中，避免回表
SELECT user_id, status FROM orders WHERE user_id = 100;
-- 如果有 idx_user_status，EXPLAIN 的 Extra 会显示 Using index

-- 利用索引做排序
SELECT * FROM orders WHERE user_id = 100 ORDER BY created_at;
-- 联合索引 idx(user_id, created_at) 可以避免 filesort
```

### 3. 索引监控

```sql
-- 查看索引使用情况
SELECT * FROM sys.schema_unused_indexes;       -- 未使用的索引
SELECT * FROM sys.schema_redundant_indexes;    -- 冗余索引
SELECT * FROM sys.schema_index_statistics ORDER BY rows_selected DESC;
```

---

## 四、SQL 语句优化

### 1. 大分页问题

```sql
-- ❌ 深分页，offset 越大越慢
SELECT * FROM orders ORDER BY id LIMIT 1000000, 10;

-- ✅ 延迟关联（deferred join）
SELECT o.* FROM orders o
INNER JOIN (
    SELECT id FROM orders ORDER BY id LIMIT 1000000, 10
) AS tmp ON o.id = tmp.id;

-- ✅ 游标分页（推荐，业务需配合）
SELECT * FROM orders WHERE id > #{lastId} ORDER BY id LIMIT 10;
```

### 2. JOIN 优化

```sql
-- 确保 JOIN 字段类型一致且有索引
-- 小表驱动大表（MySQL 优化器通常会自动选择，但需确认）

-- ❌ 子查询可能效率低
SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE age > 20);

-- ✅ 改用 JOIN
SELECT o.* FROM orders o
INNER JOIN users u ON o.user_id = u.id
WHERE u.age > 20;

-- ✅ 如果必须用子查询，EXISTS 通常优于 IN（大数据集）
SELECT * FROM orders o
WHERE EXISTS (SELECT 1 FROM users u WHERE u.id = o.user_id AND u.age > 20);
```

### 3. COUNT 优化

```sql
-- COUNT(*) 与 COUNT(1) 性能相同，MySQL 优化器会选最小的索引树
-- COUNT(column) 不统计 NULL 值

-- 精确计数大表时，可以考虑：
-- 1. 维护计数表（写入时同步更新）
-- 2. 使用近似值
SELECT TABLE_ROWS FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mydb' AND TABLE_NAME = 'orders';
```

### 4. UPDATE / DELETE 大批量操作

```sql
-- ❌ 一次性删除大量数据，锁表时间长
DELETE FROM logs WHERE created_at < '2023-01-01';

-- ✅ 分批删除
DELETE FROM logs WHERE created_at < '2023-01-01' ORDER BY id LIMIT 5000;
-- 循环执行直到影响行数为 0

-- ✅ 如果是整个分区的数据，直接 TRUNCATE 分区
ALTER TABLE logs TRUNCATE PARTITION p2022;
```

---

## 五、表结构优化

### 1. 字段选型

```
┌──────────────────────────────────────────────────┐
│  原则: 能用小类型就不用大类型，够用就行             │
├──────────────────────────────────────────────────┤
│  主键      → bigint auto_increment               │
│  状态/枚举 → tinyint（而非 varchar）              │
│  金额      → DECIMAL(10,2)（绝不用 float/double）│
│  时间      → DATETIME 或 TIMESTAMP               │
│  短文本    → VARCHAR(N)，N 刚好够用               │
│  UUID      → 存为 BINARY(16) 而非 VARCHAR(36)    │
└──────────────────────────────────────────────────┘
```

### 2. 范式与反范式

```
第三范式 → 减少冗余，写入性能好，查询需 JOIN
反范式   → 适当冗余，减少 JOIN，读取性能好

实践中常用"适度反范式"：高频查询涉及的字段适当冗余
```

---

## 六、锁问题定位

### 1. 查看当前锁等待

```sql
-- MySQL 8.0+
SELECT * FROM performance_schema.data_lock_waits;
SELECT * FROM performance_schema.data_locks;
SELECT * FROM sys.innodb_lock_waits\G

-- 查看阻塞链
SELECT
    r.trx_id AS waiting_trx_id,
    r.trx_mysql_thread_id AS waiting_thread,
    r.trx_query AS waiting_query,
    b.trx_id AS blocking_trx_id,
    b.trx_mysql_thread_id AS blocking_thread,
    b.trx_query AS blocking_query
FROM information_schema.innodb_lock_waits w
INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id;

-- 核查后，KILL 掉阻塞线程
KILL <blocking_thread_id>;
```

### 2. 死锁分析

```sql
-- 查看最近一次死锁日志
SHOW ENGINE INNODB STATUS\G
-- 在 LATEST DETECTED DEADLOCK 部分查看

-- 开启死锁日志记录
SET GLOBAL innodb_print_all_deadlocks = ON;
```

### 3. 长事务排查

```sql
SELECT
    trx_id, trx_state, trx_started,
    TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS duration_sec,
    trx_mysql_thread_id, trx_query
FROM information_schema.innodb_trx
ORDER BY trx_started ASC;

-- 配合 KILL 线程处理
```

---

## 七、连接问题定位

### 1. 连接数监控

```sql
SHOW STATUS LIKE 'Threads_connected';    -- 当前连接数
SHOW STATUS LIKE 'Threads_running';      -- 活跃线程数
SHOW VARIABLES LIKE 'max_connections';   -- 最大连接数

-- 连接使用率
-- Threads_connected / max_connections > 80% 时需警惕
```

### 2. 连接打满排查

```sql
-- 查看所有连接状态
SHOW FULL PROCESSLIST;

-- 按状态统计
SELECT command, COUNT(*) FROM information_schema.processlist GROUP BY command;

-- 常见问题：
-- Sleep 过多 → 应用连接池配置不合理（未复用、未回收）
-- Locked     → 大量锁等待
-- query 值大 → 慢查询堆积
```

---

## 八、内存与 Buffer Pool 优化

### 1. InnoDB Buffer Pool

```sql
-- 建议设为物理内存的 60%~80%
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW STATUS LIKE 'Innodb_buffer_pool_read%';

-- 命中率计算
-- 命中率 = 1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)
-- 应 > 99%
```

### 2. 关键内存参数

```ini
[mysqld]
innodb_buffer_pool_size = 12G         # Buffer Pool 大小
innodb_buffer_pool_instances = 8      # 多实例减少并发争用
innodb_log_buffer_size = 64M          # redo log buffer
sort_buffer_size = 4M                 # 每个连接的排序缓冲
join_buffer_size = 4M                 # 每个连接的 JOIN 缓冲
tmp_table_size = 64M                  # 内存临时表大小
max_heap_table_size = 64M             # 内存临时表大小
```

---

## 九、常用诊断工具速查

```
┌─────────────────────────┬──────────────────────────────────┐
│ 工具/命令                │ 用途                              │
├─────────────────────────┼──────────────────────────────────┤
│ SHOW PROCESSLIST        │ 查看当前所有连接和正在执行的SQL     │
│ SHOW ENGINE INNODB STATUS│ InnoDB 引擎状态（锁、死锁、缓冲） │
│ EXPLAIN / EXPLAIN FORMAT│ 分析执行计划                       │
│ sys schema              │ 性能诊断视图集合                   │
│ performance_schema      │ 底层性能数据采集                   │
│ SHOW STATUS LIKE '...'  │ 各类计数器和状态值                 │
│ pt-query-digest         │ 慢查询日志聚合分析                 │
│ pt-online-schema-change │ 在线DDL变更                       │
│ mysqladmin processlist  │ 命令行快速查看连接                 │
│ innodb_trx / data_locks │ 事务和锁排查                      │
└─────────────────────────┴──────────────────────────────────┘
```

---

## 十、一个完整的排查思路

```
应用反馈慢
   │
   ├── 1. SHOW PROCESSLIST → 是连接打满？锁等待？还是大查询？
   │
   ├── 2. 开启慢查询日志 → 定位到具体 SQL
   │
   ├── 3. EXPLAIN 该 SQL → 是否全表扫描？索引是否命中？
   │       │
   │       ├── type=ALL → 添加合适的索引
   │       ├── Using filesort → 优化 ORDER BY / 利用索引排序
   │       └── Using temporary → 优化 GROUP BY / 子查询
   │
   ├── 4. 检查表结构 → 字段类型是否合理？是否需要分区？
   │
   ├── 5. 检查服务器资源 → CPU / IO / 内存 / Buffer Pool 命中率
   │
   └── 6. 检查配置参数 → 连接数、缓冲区、排序缓冲等
```

这个流程基本覆盖了日常 90% 以上的 MySQL 性能问题。实际场景中，大多数问题都出在**缺少合适的索引**和**不合理的 SQL 写法**上，EXPLAIN 是最常使用的工具。
