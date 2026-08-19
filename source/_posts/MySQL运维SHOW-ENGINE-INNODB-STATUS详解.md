---
title: MySQL运维SHOW ENGINE INNODB STATUS详解
date: 2026-09-08 00:00:00
tags:
  - MySQL
  - InnoDB
  - 运维
  - DBA
categories:
  - MySQL
---

## 一、概述

`SHOW ENGINE INNODB STATUS` 是 InnoDB 存储引擎最重要的诊断命令之一，它输出 InnoDB 引擎内部大量运行时状态信息，是排查性能问题、死锁、内存异常等故障的**核心工具**。

```sql
SHOW ENGINE INNODB STATUS\G
```

> `\G` 替代 `;` 以纵向格式输出，便于阅读长文本。

输出的信息**默认是过去约 60 秒的采样快照**（非实时累计值）。

---

## 二、输出结构总览

输出内容是一个大文本块，按以下主要段落组织：

```
=====================================
[各段落名称]                         ← 段标题
=====================================
...具体数据...
```

主要段落如下：

| 段落标识 | 含义 | 重要程度 |
|---|---|---|
| **HEADER** | 版本、名称、状态信息 | ★★ |
| **SEMAPHORES** | 信号量/互斥锁等待 | ★★★★★ |
| **LATEST DETECTED DEADLOCK** | 最近一次死锁详情 | ★★★★★ |
| **TRANSACTIONS** | 事务信息 | ★★★★★ |
| **FILE I/O** | 文件 I/O 线程状态 | ★★★ |
| **INSERT BUFFER AND ADAPTIVE HASH INDEX** | 插入缓冲 & AHI | ★★★ |
| **LOG** | Redo Log 状态 | ★★★★ |
| **BUFFER POOL AND MEMORY** | Buffer Pool 内存状态 | ★★★★ |
| **ROW OPERATIONS** | 行操作统计 | ★★★ |

---

## 三、逐段详解

### 1. HEADER 段

```
=====================================
2024-01-15 10:30:00 0x7f3c8c1ff700 INNODB MONITOR OUTPUT
=====================================
Per second averages calculated from the last 43 seconds
```

- 告诉你这份快照的**采样时间窗口**是多少秒
- 正常情况下约 60 秒，如果系统非常繁忙可能更长

---

### 2. SEMAPHORES 段 — 锁等待与互斥量

```text
----------
SEMAPHORES
----------
--Thread 140737488344832 has waited at row0sel.cc line 3087 for 2.00 seconds:
  Mutex at 0x7f3c000b8720 '&buf_block->mutex'
  waiters flag: 1
  lock_word: 0
  Last time reserved: trx0purge.cc line 281

OS WAIT ARRAY INFO: reservation count 12345, signal count 67890
--Thread 140737488290560 has waited at btr0cur.cc line 622 for 3.00 seconds:
  RW-shared lock on &dict_operation_lock
```

**重点关注：**

| 关注点 | 说明 |
|---|---|
| `has waited ... for X seconds` | 某线程等待某个锁超过 X 秒，**超过 10 秒**通常说明有严重问题 |
| `Mutex` / `RW-shared` / `RW-exclusive` | 锁类型：互斥量 / 共享读锁 / 排他写锁 |
| `waited at [source file] line [N]` | 等待发生的源码位置，可用于搜索 MySQL Bug |
| `reservation count` vs `signal count` | 如果 reservation count 远大于 signal count，表示 OS 层面大量等待 |

**典型问题：**
- Buffer Pool 热点争用（大并发写入）
- `dict_operation_lock` 被持有 → DDL 操作阻塞
- 大量 `&buf_block->mutex` 等待 → 数据页争用严重

---

### 3. LATEST DETECTED DEADLOCK 段 — 死锁

```text
------------------------
LATEST DETECTED DEADLOCK
------------------------
2024-01-15 10:25:33 0x7f3c8c1ff700
*** (1) TRANSACTION:
TRANSACTION 12345, ACTIVE 3 sec starting index read
mysql tables in use 1, locked 1
LOCK WAIT 3 lock struct(s), heap size 1136, 2 row lock(s)
MySQL thread id 100, OS thread handle 140737488344832, query id 2000 localhost root updating
UPDATE t SET col = 1 WHERE id = 10

*** (1) WAITING FOR THIS LOCK TO BE GRANTED:
RECORD LOCKS space id 5 page no 3 n bits 72 index PRIMARY of table `test`.`t`
  trx id 12345 lock_mode X locks rec but not gap waiting

*** (2) TRANSACTION:
TRANSACTION 12346, ACTIVE 5 sec starting index read
...
UPDATE t SET col = 2 WHERE id = 20

*** (2) HOLDS THE LOCK(S):
RECORD LOCKS space id 5 page no 3 n bits 72 index PRIMARY of table `test`.`t`
  trx id 12346 lock_mode X locks rec but not gap

*** (2) WAITING FOR THIS LOCK TO BE GRANTED:
RECORD LOCKS space id 5 page no 3 n bits 72 index PRIMARY of table `test`.`t`
  trx id 12346 lock_mode X locks rec but not gap waiting

*** WE ROLL BACK TRANSACTION (1)
```

**解读要点：**

```
事务(1) 等待锁  ←→  事务(2) 持有该锁
事务(2) 等待锁  ←→  事务(1) 持有该锁   → 环路形成 → 死锁
```

| 字段 | 含义 |
|---|---|
| `lock_mode X locks rec but not gap` | 行级排他锁（非间隙锁） |
| `lock_mode X locks gap before rec` | 间隙锁 |
| `lock_mode X` (无 rec/gap) | Next-Key Lock |
| `lock_mode S` | 共享锁 |
| `WE ROLL BACK TRANSACTION (1)` | InnoDB 回滚了代价更小的事务 |

**排查思路：**
- 找出两个事务各自的 **SQL 语句**
- 分析其**加锁顺序**是否一致
- 调整为**统一的加锁顺序**来消除死锁

---

### 4. TRANSACTIONS 段 — 事务信息

```text
------------
TRANSACTIONS
------------
Trx id counter 500000
Purge done for trx's n:o < 499900 undo n:o < 0 state: running
History list length 350

LIST OF TRANSACTIONS FOR EACH SESSION:
---TRANSACTION 499990, ACTIVE 120 sec
mysql tables in use 1, locked 1
LOCK WAIT 2 lock struct(s), heap size 1136, 1 row lock(s)
MySQL thread id 50, query id 3000 localhost root updating
UPDATE orders SET status = 1 WHERE order_id = 100
------- TRX HAS BEEN WAITING 30 SEC FOR THIS LOCK TO BE GRANTED:
RECORD LOCKS space id 10 page no 5 ... index idx_order of table `shop`.`orders`
  trx id 499990 lock_mode X locks rec but not gap waiting
----------------------------------

---TRANSACTION 499985, ACTIVE 300 sec
3 lock struct(s), heap size 1136, 5 row lock(s), undo log entries 12
MySQL thread id 45, query id 2900 localhost root
```

**重点字段：**

| 字段 | 含义 | 关注阈值 |
|---|---|---|
| `ACTIVE X sec` | 事务活跃时长 | > 60s 需关注，长事务是大敌 |
| `undo log entries N` | 生成了多少 undo log 记录 | 越大说明修改越多 |
| `History list length` | purge 链表长度 | > 1000 需关注，说明 undo 空间回收不及时 |
| `LOCK WAIT` | 正在等待锁 | 排查锁等待 |
| `Trx id counter` vs `Purge done for trx's n:o` | 差值过大 | 说明存在老事务阻止 purge |

**长事务的危害：**

```
长事务存在
  → undo log 无法被 purge
  → ibdata1 / undo tablespace 膨胀
  → History list length 增长
  → MVCC 扫描链变长 → 查询变慢
```

查看当前所有长事务：
```sql
SELECT * FROM information_schema.INNODB_TRX 
ORDER BY trx_started ASC;
```

---

### 5. FILE I/O 段

```text
--------
FILE I/O
--------
I/O thread 0 state: waiting for completed aio requests (insert buffer thread)
I/O thread 1 state: waiting for completed aio requests (log thread)
I/O thread 2 state: waiting for completed aio requests (read thread)
...
Pending normal aio reads: [0, 0, 0, 0]
Pending normal aio writes: [0, 0, 0, 0]
Pending ibuf aio reads: 0
Pending log i/o's: 0
Pending syncs and fsyncs: 0

OS file reads: 12345, writes: 67890, fsyncs: 23456
```

**关注点：**

| 指标 | 说明 |
|---|---|
| `Pending normal aio reads/writes` | 非零值表示 I/O 有积压 |
| `Pending log i/o's` | 非零表示 Redo Log 写入有积压 |
| `state: waiting for completed aio requests` | 正常等待状态 |
| `state: doing sync/flush` | 正在做刷盘 |

---

### 6. LOG 段 — Redo Log

```text
-----
LOG
-----
Log sequence number 1234567890
Log buffer assigned up to 1234560000
Log buffer completed up to 1234550000
Log written up to 1234540000
Pages flushed up to 1234500000
Last checkpoint at 1234400000

0 pending log flushes, 0 pending chkp writes
15687 log i/o's done, 0.00 log i/o's/second
```

**关键计算：**

```
未刷盘的 Redo 量 = Log sequence number - Last checkpoint at
                 = 1234567890 - 1234400000
                 = 167890 bytes (~164 KB)
```

| 场景 | 表现 |
|---|---|
| 未刷盘量接近 `innodb_log_file_size` | 产生频繁的 checkpoint → 性能抖动 |
| `Log sequence number` 增长过快 | 说明写入压力大 |
| **建议** | 未刷盘量保持在 log file 大小的 **75% 以内** |

MySQL 8.0 中可动态调整：
```sql
ALTER INSTANCE DISABLE INNODB REDO_LOG;   -- 慎用，测试场景
SET GLOBAL innodb_redo_log_capacity = 2147483648;  -- 2GB
```

---

### 7. BUFFER POOL AND MEMORY 段

```text
----------------------
BUFFER POOL AND MEMORY
----------------------
Total large memory allocated 137428992
Dictionary memory allocated 245678
Buffer pool size   8192
Free buffers       1024
Database pages     6656
Old database pages 2457
Modified db pages  256
Pending reads      0
Pending writes: LRU 0, flush list 0, single page 0
Pages made young 12345, not young 67890
0.00 youngs/s, 0.00 non-youngs/s
Pages read 5000, created 20000, written 30000
0.00 reads/s, 0.00 creates/s, 0.00 writes/s
Buffer pool hit rate 999 / 1000
```

**核心指标：**

| 指标 | 含义 | 正常值 |
|---|---|---|
| `Buffer pool hit rate` | 缓冲池命中率 | **995+ / 1000** (99.5%+) |
| `Free buffers` | 空闲页数 | 应 > 0，为 0 说明 BP 不足 |
| `Modified db pages` | 脏页数 | 过大说明刷盘跟不上 |
| `youngs/s` vs `non-youngs/s` | LRU 热端/冷端访问频率 | 比例合理 |
| `Pending reads/writes` | 积压的读写 | 应接近 0 |

**脏页比例：**
```
脏页比例 = Modified db pages / Buffer pool size
         = 256 / 8192
         = 3.1%

-- 超过 innodb_max_dirty_pages_pct (默认90) 会强制刷盘
-- 实际建议控制在 50% 以内
```

---

### 8. ROW OPERATIONS 段

```text
--------------
ROW OPERATIONS
--------------
0 queries inside InnoDB, 0 queries in queue
0 read views open inside InnoDB
Process id=12345, Main thread id=140737488344832, state: sleeping
Number of rows inserted 100000, updated 50000, deleted 10000, read 5000000
0.00 inserts/s, 0.00 updates/s, 0.00 deletes/s, 0.00 reads/s
```

| 指标 | 含义 |
|---|---|
| `queries inside InnoDB` | InnoDB 内部正在执行的查询数 |
| `queries in queue` | 排队等待进入 InnoDB 的查询数 |
| `state: sleeping` | 主线程空闲 |
| `state: flushing buffer pool` | 正在刷 Buffer Pool |
| rows inserted/updated/deleted/read | 累计值变化趋势 |

---

## 四、实用排查场景

### 场景 1：排查死锁

```sql
-- 1. 获取死锁信息
SHOW ENGINE INNODB STATUS\G
-- 找到 LATEST DETECTED DEADLOCK 段

-- 2. 开启死锁日志到错误日志
SET GLOBAL innodb_print_all_deadlocks = ON;

-- 3. 查看错误日志
-- tail -f /var/log/mysql/error.log | grep -A50 "LATEST DETECTED DEADLOCK"
```

### 场景 2：排查锁等待

```sql
-- 结合 performance_schema（MySQL 5.7+）
SELECT * FROM performance_schema.data_lock_waits;
SELECT * FROM performance_schema.data_locks;

-- MySQL 8.0 废弃了旧的 INNODB_LOCKS / INNODB_LOCK_WAITS
```

### 场景 3：监控 Buffer Pool 健康度

```bash
# 提取命中率
mysql -e "SHOW ENGINE INNODB STATUS\G" | grep "Buffer pool hit rate"
# 输出: Buffer pool hit rate 999 / 1000

# 提取脏页数
mysql -e "SHOW ENGINE INNODB STATUS\G" | grep "Modified db pages"
```

### 场景 4：排查长事务

```sql
-- 先看 InnoDB STATUS 中 TRANSACTIONS 段
-- 再用精确查询
SELECT 
    trx_id,
    trx_state,
    trx_started,
    TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS duration_sec,
    trx_rows_modified,
    trx_query
FROM information_schema.INNODB_TRX 
WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 60
ORDER BY trx_started ASC;
```

### 场景 5：检查 Redo Log 压力

```bash
mysql -e "SHOW ENGINE INNODB STATUS\G" | grep -A20 "^LOG"

# 手动计算未刷盘量
# Log sequence number - Last checkpoint at
```

---

## 五、自动化监控脚本示例

```bash
#!/bin/bash
# innodb_status_monitor.sh

STATUS=$(mysql -e "SHOW ENGINE INNODB STATUS\G" 2>/dev/null)

# 1. 检查是否有长时间信号量等待
LONG_WAIT=$(echo "$STATUS" | grep "has waited" | awk -F'for ' '{print $2}' | awk '{print $1}' | sort -rn | head -1)
if [ "${LONG_WAIT%.*}" -gt 10 ] 2>/dev/null; then
    echo "[ALERT] Semaphore wait > 10s: ${LONG_WAIT}s"
fi

# 2. 检查缓冲池命中率
HIT_RATE=$(echo "$STATUS" | grep "Buffer pool hit rate" | awk -F'rate ' '{print $1}' | awk '{print $NF}')
echo "[INFO] Buffer pool hit rate: ${HIT_RATE}"

# 3. 检查 History list length
HISTORY=$(echo "$STATUS" | grep "History list length" | awk '{print $NF}')
if [ "$HISTORY" -gt 1000 ] 2>/dev/null; then
    echo "[WARN] History list length: ${HISTORY}"
fi

# 4. 检查死锁
if echo "$STATUS" | grep -q "LATEST DETECTED DEADLOCK"; then
    DEADLOCK_TIME=$(echo "$STATUS" | grep -A1 "LATEST DETECTED DEADLOCK" | tail -1)
    echo "[WARN] Recent deadlock detected: ${DEADLOCK_TIME}"
fi

# 5. 脏页比例
MODIFIED=$(echo "$STATUS" | grep "Modified db pages" | awk '{print $NF}')
POOL_SIZE=$(echo "$STATUS" | grep "Buffer pool size" | awk '{print $NF}')
if [ "$MODIFIED" -gt 0 ] && [ "$POOL_SIZE" -gt 0 ] 2>/dev/null; then
    DIRTY_PCT=$((MODIFIED * 100 / POOL_SIZE))
    echo "[INFO] Dirty page ratio: ${DIRTY_PCT}%"
    [ "$DIRTY_PCT" -gt 50 ] && echo "[WARN] Dirty page ratio > 50%!"
fi
```

---

## 六、MySQL 8.0 补充说明

| 变更 | 说明 |
|---|---|
| `innodb_print_all_deadlocks` | 推荐开启，所有死锁写入 error log |
| `data_locks` / `data_lock_waits` | 替代旧的 `INNODB_LOCKS` 等表 |
| `innodb_redo_log_capacity` | 8.0.30+ 替代 `innodb_log_file_size` |
| Performance Schema | 提供更细粒度的 `wait/synch/mutex/innodb/*` 事件 |

---

## 七、总结速查

```
SHOW ENGINE INNODB STATUS 核心检查清单
═══════════════════════════════════════
✅ SEMAPHORES       → 等待是否 > 10s？争用热点在哪？
✅ LATEST DEADLOCK  → 死锁涉及哪两条SQL？加锁顺序？
✅ TRANSACTIONS     → 有无长事务？History list 是否过长？
✅ FILE I/O         → Pending 数是否 > 0？I/O 是否积压？
✅ LOG              → 未刷盘 Redo 是否接近 log 容量？
✅ BUFFER POOL      → 命中率是否 > 99.5%？空闲页是否充足？
✅ ROW OPERATIONS   → queries in queue 是否 > 0？
```

这个命令是 InnoDB 运维诊断的**第一道防线**，建议定期采集并建立基线，当指标偏离基线时及时告警。
