---
title: MySQL CPU 性能定位
date: 2026-09-08 00:30:00
tags:
  - MySQL
  - CPU
  - 性能优化
  - DBA
categories:
  - MySQL
---

## 一、快速定位流程

```
OS层定位 → MySQL连接层 → SQL层 → 存储引擎层
```

---

## 二、OS 层：确认 CPU 消耗来源

### 1. 整体负载判断

```bash
# 查看整体负载
top -c
htop

# 关键指标
# %us — 用户态CPU（MySQL查询处理）
# %sy — 内核态CPU（上下文切换、锁争用）
# %wa — IO等待
# %id — 空闲
```

**经验判断：**
- `%us` 高 → MySQL 计算密集型查询（排序、聚合、函数计算）
- `%sy` 高 → 可能存在锁争用、大量上下文切换
- `%wa` 高 → IO 瓶颈，不是 CPU 问题

### 2. 定位到具体线程

```bash
# 找到CPU消耗最高的MySQL线程
top -Hp $(pidof mysqld)

# 记录高CPU线程的TID，转成16进制
printf "0x%x\n" <TID>

# 在MySQL中查找对应线程
SELECT * FROM performance_schema.threads
WHERE THREAD_OS_ID = <TID>;
```

---

## 三、MySQL 层：定位慢查询

### 1. 开启慢查询日志

```sql
-- 查看当前配置
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- 动态开启
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;          -- 超过1秒记录
SET GLOBAL log_queries_not_using_indexes = ON;  -- 记录未走索引的查询
```

### 2. 使用 `pt-query-digest` 分析慢日志

```bash
pt-query-digest /var/log/mysql/slow.log

# 输出示例：
# Rank  Query ID           Response time  Calls  R/Call  V/M
# ==== ================== ============== ====== ======= =====
#    1  0xABC123...        1520.0000  35.2%    500  3.0400  0.12
#    2  0xDEF456...         890.0000  20.6%   2000  0.4450  0.08
```

### 3. 实时查看当前执行的查询

```sql
-- 查看所有活跃连接正在执行的SQL
SELECT
    id,
    user,
    host,
    db,
    command,
    time,
    state,
    LEFT(info, 100) AS query_preview
FROM information_schema.processlist
WHERE command != 'Sleep'
ORDER BY time DESC;

-- 或使用 performance_schema（更详细）
SELECT
    t.THREAD_ID,
    t.PROCESSLIST_ID,
    t.PROCESSLIST_USER,
    t.PROCESSLIST_DB,
    t.PROCESSLIST_TIME,
    t.PROCESSLIST_STATE,
    SQL_TEXT
FROM performance_schema.threads t
JOIN performance_schema.events_statements_current esc
    ON t.THREAD_ID = esc.THREAD_ID
WHERE t.TYPE = 'FOREGROUND'
    AND t.PROCESSLIST_STATE IS NOT NULL
ORDER BY t.PROCESSLIST_TIME DESC;
```

---

## 四、Performance Schema 深度分析

### 1. 找出 CPU 消耗最高的 SQL（按总执行时间排序）

```sql
-- Top 10 最耗时SQL
SELECT
    DIGEST_TEXT,
    COUNT_STAR        AS exec_count,
    ROUND(SUM_TIMER_WAIT / 1e12, 2)   AS total_time_sec,
    ROUND(AVG_TIMER_WAIT / 1e12, 4)   AS avg_time_sec,
    SUM_ROWS_EXAMINED  AS rows_examined,
    SUM_ROWS_SENT      AS rows_sent,
    ROUND(SUM_ROWS_EXAMINED / COUNT_STAR, 0) AS avg_rows_examined
FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 10;
```

### 2. 识别全表扫描

```sql
-- 扫描行数远大于返回行数 → 大量无效扫描消耗CPU
SELECT
    DIGEST_TEXT,
    COUNT_STAR,
    SUM_ROWS_EXAMINED,
    SUM_ROWS_SENT,
    ROUND(SUM_ROWS_EXAMINED / GREATEST(SUM_ROWS_SENT, 1), 2) AS examine_sent_ratio
FROM performance_schema.events_statements_summary_by_digest
WHERE SUM_ROWS_EXAMINED > 0
ORDER BY examine_sent_ratio DESC
LIMIT 10;
```

> **examine_sent_ratio** 越大，说明扫描了大量数据只返回很少结果，索引设计可能有问题。

### 3. 查看排序、临时表等 CPU 密集操作

```sql
SELECT
    DIGEST_TEXT,
    COUNT_STAR,
    SUM_SORT_ROWS,
    SUM_CREATED_TMP_TABLES,
    SUM_CREATED_TMP_DISK_TABLES,
    SUM_NO_INDEX_USED,
    SUM_NO_GOOD_INDEX_USED
FROM performance_schema.events_statements_summary_by_digest
WHERE SUM_SORT_ROWS > 0
   OR SUM_CREATED_TMP_DISK_TABLES > 0
ORDER BY SUM_SORT_ROWS DESC
LIMIT 10;
```

---

## 五、常见 CPU 高的根因及排查

### 根因 1：慢 SQL / 缺少索引

```sql
-- 对可疑SQL做EXPLAIN
EXPLAIN SELECT * FROM orders WHERE user_id = 100 ORDER BY create_time DESC;

-- 关注这些字段
-- type: ALL → 全表扫描（CPU杀手）
-- Extra: Using filesort → 排序没有走索引
-- Extra: Using temporary → 使用临时表
-- rows: 扫描行数是否过大
```

**解决：** 添加合适索引，优化查询写法。

### 根因 2：排序与临时表

```sql
-- 查看临时表使用情况
SHOW GLOBAL STATUS LIKE 'Created_tmp%';

-- Created_tmp_disk_tables 特别大时，说明内存临时表溢出到磁盘
-- 调大 tmp_table_size 和 max_heap_table_size
SET GLOBAL tmp_table_size = 256 * 1024 * 1024;
SET GLOBAL max_heap_table_size = 256 * 1024 * 1024;
```

### 根因 3：锁争用导致 CPU 飙升

```sql
-- 查看InnoDB锁等待
SELECT * FROM information_schema.INNODB_LOCK_WAITS;

-- 8.0+ 查看
SELECT * FROM performance_schema.data_lock_waits;

-- 查看InnoDB引擎状态
SHOW ENGINE INNODB STATUS\G
```

### 根因 4：大量连接 / 线程切换

```sql
-- 查看当前连接数
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL STATUS LIKE 'Threads_running';

-- Threads_running 过高时，大量线程同时执行，CPU争抢严重
-- 一般 Threads_running > CPU核心数 * 2 就需要关注
```

**解决：** 连接池限制、`thread_cache_size` 调优。

### 根因 5：函数/计算在SQL中执行

```sql
-- 典型反模式：索引列上使用函数，导致索引失效
SELECT * FROM orders WHERE DATE(create_time) = '2024-01-01';  -- 不走索引
SELECT * FROM orders WHERE create_time >= '2024-01-01'
    AND create_time < '2024-01-02';  -- 走索引

-- 隐式类型转换
SELECT * FROM users WHERE phone = 13800138000;  -- phone是varchar，不走索引
SELECT * FROM users WHERE phone = '13800138000'; -- 走索引
```

---

## 六、监控与告警工具

### 1. 关键监控指标

| 指标 | 含义 | 告警阈值参考 |
|------|------|-------------|
| `Threads_running` | 活跃线程数 | > CPU核数×2 |
| `Questions` / QPS | 每秒查询数 | 根据基线判断 |
| `Slow_queries` | 慢查询数 | > 0 持续增长 |
| `Created_tmp_disk_tables` | 磁盘临时表 | 占比 > 10% 需关注 |
| `Select_full_join` | 无索引JOIN | > 0 需立即处理 |
| `Table_locks_waited` | 表锁等待 | 持续 > 0 需关注 |

### 2. 快速诊断脚本

```sql
-- 一键查看关键状态
SELECT
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status
     WHERE VARIABLE_NAME='Threads_running') AS threads_running,
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status
     WHERE VARIABLE_NAME='Threads_connected') AS threads_connected,
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status
     WHERE VARIABLE_NAME='Slow_queries') AS slow_queries,
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status
     WHERE VARIABLE_NAME='Created_tmp_disk_tables') AS tmp_disk_tables,
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status
     WHERE VARIABLE_NAME='Select_full_join') AS full_joins;
```

---

## 七、定位流程总结

```
1. top -c / top -Hp <pid>
   ├─ 确认是 mysqld 进程消耗CPU
   └─ 找到具体高CPU线程TID

2. 慢查询日志 + pt-query-digest
   └─ 找出最耗时、执行最频繁的SQL

3. EXPLAIN 分析可疑SQL
   ├─ 全表扫描 → 加索引
   ├─ filesort → 优化ORDER BY
   └─ Using tmp → 优化GROUP BY / DISTINCT

4. SHOW PROCESSLIST
   └─ 实时查看是否有大量活跃查询、锁等待

5. Performance Schema
   ├─ events_statements_summary_by_digest → SQL维度统计
   ├─ data_lock_waits → 锁争用
   └─ threads → 线程状态

6. 系统参数调优
   ├─ sort_buffer_size / join_buffer_size
   ├─ tmp_table_size / max_heap_table_size
   ├─ innodb_buffer_pool_size
   └─ thread_cache_size
```

核心思路：**先从OS层确认是MySQL的CPU问题，再通过慢日志和Performance Schema定位到具体SQL，最后通过EXPLAIN和索引优化来解决。**
