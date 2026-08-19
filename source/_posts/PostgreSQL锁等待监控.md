---
title: PostgreSQL 锁等待监控
date: 2026-09-08 00:15:00
tags:
  - PostgreSQL
  - 锁
  - 监控
  - DBA
categories:
  - PostgreSQL
---

## 一、核心监控查询

### 1. 查看当前锁等待关系（最常用）

```sql
SELECT
    blocked_locks.pid     AS blocked_pid,
    blocked_activity.usename  AS blocked_user,
    blocking_locks.pid     AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query    AS blocked_query,
    blocking_activity.query   AS blocking_query,
    blocked_activity.application_name AS blocked_app,
    now() - blocked_activity.query_start AS waiting_duration,
    blocked_locks.locktype,
    blocked_locks.relation::regclass AS locked_table
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity
    ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.relation = blocked_locks.relation
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity
    ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted
  AND blocking_locks.granted;
```



### 2. 查看所有等待中的锁

```sql
SELECT
    l.pid,
    a.usename,
    a.state,
    l.locktype,
    l.relation::regclass AS table_name,
    l.mode,
    l.granted,
    a.query,
    now() - a.query_start AS query_duration,
    now() - a.state_change AS state_duration
FROM pg_locks l
JOIN pg_stat_activity a ON a.pid = l.pid
WHERE NOT l.granted
ORDER BY query_duration DESC;
```

### 3. 锁冲突矩阵（哪些锁模式互斥）

```sql
SELECT
    locktype,
    mode,
    COUNT(*) FILTER (WHERE NOT granted) AS waiting,
    COUNT(*) FILTER (WHERE granted)     AS granted,
    COUNT(*) AS total
FROM pg_locks
GROUP BY locktype, mode
ORDER BY locktype, mode;
```

---

## 二、锁类型详解

```
┌────────────────────┬────────────────────────────────────────────┐
│ Lock Type          │ 说明                                       │
├────────────────────┼────────────────────────────────────────────┤
│ relation           │ 表级锁（DDL、VACUUM、顺序扫描等）            │
│ tuple              │ 行级锁（UPDATE/DELETE/SELECT FOR UPDATE）    │
│ transactionid      │ 事务ID锁（写事务提交/回滚时持有）             │
│ virtualxid         │ 虚拟事务ID锁                               │
│ advisory           │ 用户自定义咨询锁（pg_advisory_lock）         │
│ object             │ 数据库对象锁（ACL 相关）                     │
│ page               │ 页级锁（某些索引操作）                       │
│ relation extension │ 关系扩展锁（表膨胀时插入需要）                │
└────────────────────┴────────────────────────────────────────────┘
```

### 表级锁模式冲突速查

```
              ACCESS  ROW     ROW     ROW     SHARE   SHARE   EXCLUSIVE  ACCESS
              SHARE   SHARE   EXCLUSIVE EXCLUSIVE UPDATE  ROW               EXCLUSIVE
                                    (KEY)             EXCLUSIVE
ACCESS SHARE    ✓       ✓       ✓       ✓       ✓       ✓        ✗          ✗
ROW SHARE       ✓       ✓       ✓       ✓       ✓       ✗        ✗          ✗
ROW EXCLUSIVE   ✓       ✓       ✓       ✓       ✗       ✗        ✗          ✗
SHARE UPDATE    ✓       ✓       ✓       ✓       ✗       ✗        ✗          ✗
EXCLUSIVE
SHARE           ✓       ✓       ✗       ✗       ✗       ✗        ✗          ✗
SHARE ROW       ✓       ✓       ✗       ✗       ✗       ✗        ✗          ✗
EXCLUSIVE
EXCLUSIVE       ✗       ✗       ✗       ✗       ✗       ✗        ✗          ✗
ACCESS          ✗       ✗       ✗       ✗       ✗       ✗        ✗          ✗
EXCLUSIVE
```

---

## 三、自动化监控脚本

### 1. 长时间锁等待告警

```sql
SELECT
    'LOCK_WAIT_ALERT' AS alert_type,
    blocked.pid    AS blocked_pid,
    blocking.pid   AS blocking_pid,
    blocked.query  AS blocked_query,
    blocking.query AS blocking_query,
    extract(epoch FROM now() - blocked.query_start)::int AS wait_seconds
FROM pg_locks bl
JOIN pg_stat_activity blocked  ON blocked.pid  = bl.pid
JOIN pg_locks kl
    ON kl.locktype    = bl.locktype
   AND kl.database    IS NOT DISTINCT FROM bl.database
   AND kl.relation    IS NOT DISTINCT FROM bl.relation
   AND kl.page        IS NOT DISTINCT FROM bl.page
   AND kl.tuple       IS NOT DISTINCT FROM bl.tuple
   AND kl.transactionid IS NOT DISTINCT FROM bl.transactionid
   AND kl.pid         != bl.pid
   AND kl.granted
JOIN pg_stat_activity blocking ON blocking.pid = kl.pid
WHERE NOT bl.granted
  AND now() - blocked.query_start > interval '30 seconds'  -- 阈值
ORDER BY wait_seconds DESC;
```



### 2. 死锁检测日志查询

```sql
-- 确认 deadlock 相关参数
SHOW deadlock_timeout;       -- 默认 1s
SHOW log_lock_waits;         -- 需要为 on 才记录锁等待
SHOW log_min_duration_statement; -- 记录慢查询的阈值

-- PostgreSQL 配置建议
-- postgresql.conf:
--   deadlock_timeout = 1s
--   log_lock_waits = on
--   log_min_duration_statement = 1000  (ms)
```

### 3. 按表统计锁争用

```sql
SELECT
    c.relname AS table_name,
    l.mode,
    COUNT(*) AS lock_count,
    COUNT(*) FILTER (WHERE NOT l.granted) AS waiting_count
FROM pg_locks l
JOIN pg_class c ON c.oid = l.relation
WHERE l.locktype = 'relation'
GROUP BY c.relname, l.mode
HAVING COUNT(*) FILTER (WHERE NOT l.granted) > 0
ORDER BY waiting_count DESC;
```

---

## 四、长期趋势监控

### 1. pg_stat_activity 快照（定时采集）

```sql
-- 创建监控表
CREATE TABLE lock_monitor_log (
    id            BIGSERIAL PRIMARY KEY,
    captured_at   TIMESTAMPTZ DEFAULT now(),
    blocked_pid   INT,
    blocking_pid  INT,
    blocked_query TEXT,
    blocked_user  VARCHAR(64),
    lock_type     VARCHAR(32),
    table_name    TEXT,
    wait_seconds  NUMERIC
);

-- 定时采集（每10秒 via pg_cron 或外部调度）
INSERT INTO lock_monitor_log
    (blocked_pid, blocking_pid, blocked_query, blocked_user,
     lock_type, table_name, wait_seconds)
SELECT
    blocked.pid,
    blocking.pid,
    blocked.query,
    blocked.usename,
    bl.locktype,
    bl.relation::regclass::text,
    extract(epoch FROM now() - blocked.query_start)
FROM pg_locks bl
JOIN pg_stat_activity blocked ON blocked.pid = bl.pid
JOIN pg_locks kl
    ON kl.locktype = bl.locktype
   AND kl.relation IS NOT DISTINCT FROM bl.relation
   AND kl.transactionid IS NOT DISTINCT FROM bl.transactionid
   AND kl.pid != bl.pid
   AND kl.granted
JOIN pg_stat_activity blocking ON blocking.pid = kl.pid
WHERE NOT bl.granted;
```

### 2. pg_stat_user_tables 锁相关指标

```sql
SELECT
    relname,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup,
    round(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2)
        AS dead_tuple_pct,
    last_vacuum,
    last_autovacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;
```

---

## 五、锁问题诊断流程

```
发现锁等待
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 1: 确认锁等待是否存在                    │
│   SELECT * FROM pg_locks WHERE NOT granted;  │
└─────────────────┬───────────────────────────┘
                  │ 有等待
                  ▼
┌─────────────────────────────────────────────┐
│ Step 2: 找出阻塞链                           │
│   使用"核心查询"找到 blocker → blocked 关系   │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 3: 分析阻塞者                           │
│   - query: 在执行什么SQL？                    │
│   - state: active/idle in transaction?       │
│   - query_start: 执行了多久？                 │
│   - 是否处于 idle in transaction (空等事务)?   │
└─────────────────┬───────────────────────────┘
                  │
           ┌──────┴──────┐
           ▼             ▼
      长事务阻塞       死锁
           │             │
           ▼             ▼
    考虑终止/Kill    检查 deadlock_timeout
    pg_terminate_    日志分析死锁SQL
    backend(pid)     优化事务顺序
```

---

## 六、常见锁问题与解决

### 1. idle in transaction（最常见元凶）

```sql
-- 找出空闲事务
SELECT
    pid,
    usename,
    state,
    query,
    now() - state_change AS idle_duration,
    now() - xact_start   AS xact_duration
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND now() - state_change > interval '5 minutes'
ORDER BY idle_duration DESC;

-- 强制终止（慎用）
SELECT pg_terminate_backend(pid);

-- 预防：设置空闲事务超时（PG 14+）
SET idle_in_transaction_session_timeout = '5min';
```

### 2. DDL 锁等待（ALTER TABLE 阻塞）

```sql
-- ALTER TABLE 需要 ACCESS EXCLUSIVE 锁
-- 会阻塞所有读写操作

-- 检查是否有 DDL 在等待
SELECT
    pid,
    wait_event_type,
    wait_event,
    state,
    query
FROM pg_stat_activity
WHERE query ~* 'ALTER|DROP|TRUNCATE|CREATE INDEX'
  AND state = 'active';

-- PG 12+ 使用：
-- CREATE INDEX CONCURRENTLY 避免写阻塞
-- ALTER TABLE ... ADD COLUMN ... DEFAULT ... 避免重写（PG 11+）
```

### 3. 行锁堆积

```sql
-- 查看单表行锁数量
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    (SELECT COUNT(*) FROM pg_locks
     WHERE relation = pg_stat_user_tables.relid
       AND locktype = 'tuple') AS tuple_locks
FROM pg_stat_user_tables
ORDER BY tuple_locks DESC
LIMIT 20;
```

### 4. Advisory Lock

```sql
-- 查看咨询锁
SELECT * FROM pg_locks WHERE locktype = 'advisory';

-- 按 application 使用
SELECT pg_advisory_lock(12345);       -- 获取
SELECT pg_advisory_unlock(12345);     -- 释放

-- 会话级（连接断开自动释放）
SELECT pg_advisory_lock(key);

-- 事务级（事务结束自动释放）
SELECT pg_advisory_xact_lock(key);
```

---

## 七、Prometheus + Grafana 监控方案

### 推荐 Exporter 配置

```yaml
# postgres_exporter 查询示例
# custom_queries.yml
pg_lock_waits:
  query: |
    SELECT
      COUNT(*) AS pg_lock_waiting_count
    FROM pg_locks
    WHERE NOT granted;
  metrics:
    - pg_lock_waiting_count:
        usage: "GAUGE"
        description: "Number of sessions waiting for locks"

pg_longest_lock_wait:
  query: |
    SELECT
      COALESCE(MAX(extract(epoch FROM now() - query_start)), 0)
        AS pg_lock_max_wait_seconds
    FROM pg_locks l
    JOIN pg_stat_activity a ON a.pid = l.pid
    WHERE NOT l.granted;
  metrics:
    - pg_lock_max_wait_seconds:
        usage: "GAUGE"
        description: "Longest lock wait duration in seconds"
```

### Grafana 关键面板

```
┌─────────────────────────────────────────────────────────┐
│  锁等待数    │   最长等待时间   │   活跃事务数  │  死锁次数  │
│  ████████    │   ████████████   │  ██████████  │ ████████  │
│  gauge       │   gauge          │  gauge       │ counter   │
├─────────────────────────────────────────────────────────┤
│  锁等待趋势图（时序）                                     │
│  ─────────────────────────────────────────               │
│       ╱╲                                                │
│  ───╱──╲──────────╱╲────                                 │
│  ╱──────────╲────╱────╲──                               │
├─────────────────────────────────────────────────────────┤
│  阻塞关系表（实时）                                       │
│  blocked_pid | blocking_pid | duration | query           │
│  12345       | 12340        | 30s      | SELECT ...       │
└─────────────────────────────────────────────────────────┘
```

---

## 八、最佳实践总结

| 实践 | 配置/操作 |
|---|---|
| 开启锁等待日志 | `log_lock_waits = on` |
| 死锁超时 | `deadlock_timeout = 1s` |
| 空闲事务超时 | `idle_in_transaction_session_timeout = '5min'` |
| DDL 超时 | `lock_timeout = '10s'`（DDL 语句前 SET） |
| 语句超时 | `statement_timeout = '30s'` |
| 长事务告警阈值 | `> 60s` 开始关注 |
| 优先使用 | `CREATE INDEX CONCURRENTLY` |
| 优先使用 | `SELECT ... FOR UPDATE NOWAIT` |
| 定期清理 | `idle in transaction` 会话 |

关键原则：**锁问题的本质通常是事务设计问题**。监控只是手段，根本解决在于控制事务粒度、缩短持锁时间、避免不必要的锁升级。
