---
title: MySQL核心参数优化指南
date: 2026-09-08 00:45:00
tags:
  - MySQL
  - 参数优化
  - InnoDB
  - DBA
categories:
  - MySQL
---

---

## 一、总纲：优化原则

在调参之前，明确三个前提：

1. **没有万能参数** —— 所有值都依赖硬件配置、数据量和业务模式。
2. **一次只改一个参数** —— 否则无法定位效果来源。
3. **监控先行** —— 调参前先用 `SHOW GLOBAL STATUS`、`Performance Schema`、`slow_query_log` 建立基线。

---

## 二、InnoDB 缓冲池（影响最大的单一参数）

### `innodb_buffer_pool_size`

```ini
# 专用数据库服务器建议：物理内存的 50%~80%
innodb_buffer_pool_size = 8G          # 例如 16G 内存的机器设为 8~12G
```

**原理**：InnoDB 将表数据和索引缓存在此池中。命中率越高，磁盘 I/O 越少。

**验证方式**：
```sql
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read%';
-- 命中率 = 1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)
-- 目标：> 99%
```

### `innodb_buffer_pool_instances`

```ini
# 每个实例至少 1G，实例数 = buffer_pool_size / 1G
# 8G 缓冲池 → 8 个实例
innodb_buffer_pool_instances = 8
```

> MySQL 8.0.20+ 已废弃此参数，由系统自动管理。

---

## 三、Redo Log 与刷盘策略

### `innodb_log_file_size`（MySQL 8.0.30+ 改为 `innodb_redo_log_capacity`）

```ini
# MySQL 8.0.30+
innodb_redo_log_capacity = 2G

# MySQL 8.0.30 之前
innodb_log_file_size = 1G
innodb_log_files_in_group = 2
```

**原则**：
- 太小 → 频繁 checkpoint → 写放大严重
- 太大 → 崩溃恢复时间变长
- 一般设为 **1~2 倍缓冲池大小**，或能容纳约 1 小时的写入量

### `innodb_flush_log_at_trx_commit`

```ini
innodb_flush_log_at_trx_commit = 1    # 默认值，最安全
```

| 值 | 行为 | 安全性 | 性能 |
|---|---|---|---|
| `1` | 每次提交都 fsync redo log | 不丢数据 | 最低 |
| `2` | 每秒 fsync，提交写 OS cache | 丢 ~1 秒数据 | 中等 |
| `0` | 每秒才写 OS cache 并 fsync | 丢 ~1 秒数据 | 最高 |

> 金融/交易场景必须为 `1`。日志/埋点等非核心场景可考虑 `2`。

### `innodb_flush_method`

```ini
# Linux 推荐，绕过 OS 文件系统缓存，减少双缓存
innodb_flush_method = O_DIRECT
```

> macOS / Windows / 某些特殊存储（如 NFS）可能不适用。

---

## 四、并发与连接管理

### `max_connections`

```ini
max_connections = 500                # 根据实际并发调整
```

**估算公式**：
```
max_connections ≈ 峰值活跃线程数 × 1.2~1.5
```

**关键**：不要设过大。每个连接约占 `thread_stack`（默认 1MB）+ `sort_buffer` + `join_buffer` 等内存。连接数过多会导致 OOM。

### `thread_cache_size`

```ini
# 缓存可复用的线程数，减少线程创建开销
thread_cache_size = 64
```

监控：
```sql
SHOW GLOBAL STATUS LIKE 'Threads_created';
-- 如果增长很快，适当增大此值
```

### `back_log`

```ini
# TCP 连接排队队列，高并发短连接场景需调大
back_log = 1024
```

---

## 五、查询执行缓冲区（Session 级别，谨慎调大）

这些是**每个连接独立分配**的，设太大会导致总内存爆炸。

| 参数 | 默认值 | 建议 | 说明 |
|---|---|---|---|
| `sort_buffer_size` | 256K | 256K ~ 4M | ORDER BY / GROUP BY 排序用 |
| `join_buffer_size` | 256K | 256K ~ 4M | 无索引的 JOIN 用 |
| `read_rnd_buffer_size` | 256K | 256K ~ 4M | 排序后读取行用 |
| `tmp_table_size` / `max_heap_table_size` | 16M / 16M | 16M ~ 128M | 内存临时表上限 |

```ini
sort_buffer_size = 2M
join_buffer_size = 2M
tmp_table_size = 64M
max_heap_table_size = 64M
```

> **核心原则**：不要随意把 session buffer 设为几百 MB。总内存 = 参数值 × max_connections，这是 OOM 的常见元凶。

---

## 六、表缓存与文件句柄

### `table_open_cache`

```ini
# MySQL 打开的表缓存数量
table_open_cache = 4096
```

```sql
SHOW GLOBAL STATUS LIKE 'Opened_tables';
-- 如果持续增长，说明缓存不够，需调大
```

### `table_open_cache_instances`

```ini
table_open_cache_instances = 16       # 减少锁竞争
```

### 操作系统层面

```bash
# /etc/security/limits.conf
mysql soft nofile 65535
mysql hard nofile 65535

# /etc/sysctl.conf
fs.file-max = 2097152
```

---

## 七、查询缓存（已废弃）

```ini
# MySQL 8.0 已彻底移除 query_cache
# MySQL 5.7 及以下：强烈建议关闭
query_cache_type = 0
query_cache_size = 0
```

**原因**：在高并发写入场景下，任何表的写操作都会使该表的所有缓存失效，导致严重的锁竞争。

---

## 八、日志与诊断

### 慢查询日志（必开）

```ini
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1                   # 超过 1 秒记录（生产可设 0.5~2）
log_queries_not_using_indexes = 1     # 记录未使用索引的查询
min_examined_row_limit = 100          # 至少扫描 100 行才记录，过滤噪音
```

### 错误日志

```ini
log_error = /var/log/mysql/error.log
log_error_verbosity = 2               # 1=errors, 2=+warnings, 3=+notes
```

### Performance Schema

```ini
performance_schema = ON               # MySQL 5.7+ 默认开启
```

---

## 九、锁与事务

### `innodb_lock_wait_timeout`

```ini
# 行锁等待超时（秒）
innodb_lock_wait_timeout = 10         # 默认 50 秒太长
```

### `innodb_deadlock_detect`

```ini
innodb_deadlock_detect = ON           # 默认开启，高并发热点行冲突严重时可考虑关闭并依赖超时
```

### `innodb_print_all_deadlocks`

```ini
# 将所有死锁信息写入错误日志，排查必备
innodb_print_all_deadlocks = ON
```

---

## 十、Binlog（主从复制相关）

```ini
binlog_format = ROW                   # 推荐 ROW 格式
sync_binlog = 1                       # 每次提交刷盘，最安全
# sync_binlog = 100                   # 每 100 次刷盘，性能更好但有丢失风险
```

> **"双一"配置**（最安全）：`innodb_flush_log_at_trx_commit = 1` + `sync_binlog = 1`

---

## 十一、内存全景估算

调参前务必计算 **最大可能内存消耗**：

```
Total = innodb_buffer_pool_size
      + key_buffer_size               (MyISAM 用，一般 128M 够)
      + max_connections × (
            thread_stack               -- 默认 1MB
          + sort_buffer_size
          + join_buffer_size
          + read_rnd_buffer_size
          + read_buffer_size
          + binlog_cache_size
          + net_buffer_length
      )
      + innodb_log_buffer_size         -- 默认 16M
      + tmp_table_size                 (每个会话独立)
      + Performance Schema 内存
      + OS 保留内存 (至少 2G)
```

> **确保 Total < 物理内存**，否则触发 swap，性能断崖式下降。

---

## 十二、推荐配置模板（16G 内存 OLTP 机器）

```ini
[mysqld]
# === 核心内存 ===
innodb_buffer_pool_size        = 8G
innodb_buffer_pool_instances   = 8

# === Redo Log ===
innodb_redo_log_capacity       = 2G
innodb_flush_log_at_trx_commit = 1
innodb_flush_method            = O_DIRECT
innodb_log_buffer_size         = 64M

# === 连接 ===
max_connections                = 500
thread_cache_size              = 64
back_log                       = 1024

# === Session Buffers ===
sort_buffer_size               = 2M
join_buffer_size               = 2M
read_rnd_buffer_size           = 2M
tmp_table_size                 = 64M
max_heap_table_size            = 64M

# === 表缓存 ===
table_open_cache               = 4096
table_open_cache_instances     = 16

# === 锁 ===
innodb_lock_wait_timeout       = 10
innodb_print_all_deadlocks     = ON

# === Binlog ===
binlog_format                  = ROW
sync_binlog                    = 1

# === 日志 ===
slow_query_log                 = ON
slow_query_log_file            = /var/log/mysql/slow.log
long_query_time                = 1
log_queries_not_using_indexes  = ON
log_error                      = /var/log/mysql/error.log
log_error_verbosity            = 2
```

---

## 十三、调参工作流

```
 ┌──────────────┐
 │  1. 建立基线  │  SHOW GLOBAL STATUS + 慢查询日志
 └──────┬───────┘
        ▼
 ┌──────────────────┐
 │  2. 定位瓶颈      │  CPU? I/O? 锁? 内存?
 └──────┬───────────┘
        ▼
 ┌──────────────────┐
 │  3. 修改单一参数   │  每次只改一个
 └──────┬───────────┘
        ▼
 ┌──────────────────┐
 │  4. 压测验证       │  sysbench / 生产灰度
 └──────┬───────────┘
        ▼
 ┌──────────────────┐
 │  5. 对比基线       │  有效 → 保留；无效/退化 → 回滚
 └──────┘
```

---

调参是持续过程，不是一次性动作。业务增长、数据膨胀、硬件更替都可能需要重新审视这些参数。最重要的一步永远是**先监控，再调优**。
