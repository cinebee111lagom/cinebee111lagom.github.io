---
title: sysbench 全面性能测试指南
date: 2026-09-07 23:30:00
tags:
  - sysbench
  - 性能测试
  - MySQL
  - Linux
categories:
  - MySQL
---

sysbench 是一款开源的多线程基准测试工具，支持以下 **七大测试领域**：

---

## 一、CPU 运算性能测试

测试 CPU 的整数运算能力，默认通过**素数计算**来评估。

```bash
# 计算素数上限为 10000，使用 4 个线程，运行 60 秒
sysbench cpu --cpu-max-prime=10000 --threads=4 --time=60 run
```

**关键参数：**
- `--cpu-max-prime`：素数上限值，值越大计算量越重
- `--threads`：并发线程数，通常设置为 CPU 核心数

**核心指标：**
- `total events` — 总完成次数
- `events per second` — 每秒运算次数（**越高越好**）
- `total time` — 总耗时

---

## 二、磁盘 I/O 性能测试

测试文件系统的读写性能，模拟不同 I/O 模式。

```bash
# 1. 准备测试文件（默认在当前目录生成）
sysbench fileio \
  --file-total-size=10G \
  --file-test-mode=rndrw \
  prepare

# 2. 执行测试
sysbench fileio \
  --file-total-size=10G \
  --file-test-mode=rndrw \
  --file-extra-flags=direct \
  --file-fsync-freq=0 \
  --file-num=64 \
  --threads=4 \
  --time=60 \
  run

# 3. 清理测试文件
sysbench fileio cleanup
```

**I/O 测试模式（`--file-test-mode`）：**

| 模式 | 说明 |
|---|---|
| `seqwr` | 顺序写 |
| `seqrewr` | 顺序重写 |
| `seqrd` | 顺序读 |
| `rndrd` | 随机读 |
| `rndwr` | 随机写 |
| `rndrw` | 随机读写（**最常用**） |

**核心指标：**
- `read/write MiB/s` — 读写吞吐量
- `read/write requests/s` — 每秒 I/O 请求数（IOPS）
- `95th percentile` — 95% 请求的延迟（**越低越好**）

---

## 三、调度程序性能测试

测试操作系统**线程调度器**的性能，评估在大量线程竞争下的调度效率。

```bash
sysbench threads \
  --threads=256 \
  --thread-yields=1000 \
  --thread-locks=8 \
  --time=60 \
  run
```

**关键参数：**
- `--thread-yields`：每次请求的 yield 次数
- `--thread-locks`：每次请求的锁数量

**核心指标：**
- `total events` — 调度完成总次数
- `events per second` — 每秒调度次数

> 该测试反映的是操作系统内核调度器在高并发场景下的效率。

---

## 四、内存分配及传输速度测试

测试内存的读写带宽和分配/释放性能。

```bash
# 测试内存写入，块大小为 1K，总传输量 100G
sysbench memory \
  --memory-block-size=1K \
  --memory-total-size=100G \
  --memory-oper=write \
  --memory-access-mode=seq \
  --threads=4 \
  run
```

**关键参数：**

| 参数 | 说明 |
|---|---|
| `--memory-block-size` | 内存块大小（默认 1K） |
| `--memory-total-size` | 总传输数据量 |
| `--memory-oper` | 操作类型：`write`（写）/ `read`（读） |
| `--memory-access-mode` | 访问模式：`seq`（顺序）/ `rnd`（随机） |

**核心指标：**
- `transferred (MiB/sec)` — **内存传输速率**（最重要的指标）
- `total time` — 总耗时

---

## 五、POSIX 线程性能测试

测试 POSIX 线程的**互斥锁（mutex）** 竞争性能。

```bash
sysbench mutex \
  --mutex-num=4096 \
  --mutex-locks=500000 \
  --mutex-loops=10000 \
  --threads=64 \
  run
```

**关键参数：**
- `--mutex-num`：互斥锁的数量
- `--mutex-locks`：每个线程执行的锁操作次数
- `--mutex-loops`：获取锁后执行的空循环次数

**核心指标：**
- `total time` — 总耗时（**越短越好**）

> 该测试反映系统在锁竞争场景下线程同步的效率。

---

## 六、数据库 OLTP 性能测试

这是 sysbench **最核心、最常用**的功能，模拟真实 OLTP 事务负载。

测试通过 `/usr/share/sysbench/` 目录下的 Lua 脚本执行：

```bash
ls /usr/share/sysbench/
# 常见脚本：
# oltp_read_only.lua       — 只读测试
# oltp_read_write.lua      — 读写混合测试
# oltp_write_only.lua      — 纯写入测试
# oltp_insert.lua          — 插入测试
# oltp_point_select.lua    — 点查测试
# oltp_update_index.lua    — 更新（带索引）测试
# oltp_delete.lua          — 删除测试
```

### 完整示例（MySQL 读写混合测试）

```bash
# ===== 第一步：准备测试数据 =====
sysbench /usr/share/sysbench/oltp_read_write.lua \
  --mysql-host=127.0.0.1 \
  --mysql-port=3306 \
  --mysql-user=root \
  --mysql-password=your_password \
  --mysql-db=sbtest \
  --tables=10 \
  --table-size=1000000 \
  prepare

# ===== 第二步：执行测试 =====
sysbench /usr/share/sysbench/oltp_read_write.lua \
  --mysql-host=127.0.0.1 \
  --mysql-port=3306 \
  --mysql-user=root \
  --mysql-password=your_password \
  --mysql-db=sbtest \
  --tables=10 \
  --table-size=1000000 \
  --threads=16 \
  --time=300 \
  --report-interval=10 \
  --histogram \
  run

# ===== 第三步：清理数据 =====
sysbench /usr/share/sysbench/oltp_read_write.lua \
  --mysql-host=127.0.0.1 \
  --mysql-user=root \
  --mysql-password=your_password \
  --mysql-db=sbtest \
  --tables=10 \
  cleanup
```

**OLTP 测试核心指标：**

| 指标 | 含义 |
|---|---|
| `transactions per second (TPS)` | **每秒事务数**（最核心） |
| `queries per second (QPS)` | 每秒查询数 |
| `95th percentile (ms)` | P99 延迟 |
| `total number of events` | 总事务数 |
| `deadlocks` | 死锁次数（应为 0） |

---

## 七、自定义 Lua 脚本测试

sysbench 支持编写**自定义 Lua 脚本**，实现灵活的测试场景。

### 编写自定义脚本示例

```lua
-- my_custom_test.lua
-- 自定义一个简单的点查 + 范围查询混合测试

pathtest = string.match("(.-)([^\\/]-%.?([^%.\\/]*))$", "") .. "./"

function prepare()
   -- 准备阶段：创建表
   db_query("CREATE TABLE IF NOT EXISTS custom_test ("
         .. "id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
         .. "k INT NOT NULL DEFAULT 0, "
         .. "c CHAR(120) NOT NULL DEFAULT '', "
         .. "pad CHAR(60) NOT NULL DEFAULT ''"
         .. ")")
end

function event()
   -- 每次事件：执行一条随机点查
   local id = sysbench.rand.uniform(1, 100000)
   db_query("SELECT * FROM custom_test WHERE id = " .. id)
end

function cleanup()
   -- 清理阶段：删除表
   db_query("DROP TABLE IF EXISTS custom_test")
end
```

### 运行自定义脚本

```bash
sysbench my_custom_test.lua \
  --mysql-host=127.0.0.1 \
  --mysql-user=root \
  --mysql-password=your_password \
  --mysql-db=sbtest \
  --threads=8 \
  --time=120 \
  prepare run cleanup
```

### Lua 脚本可用的回调函数

| 函数 | 作用 |
|---|---|
| `prepare()` | 测试前的数据准备 |
| `event()` | **每次迭代执行的操作**（核心） |
| `cleanup()` | 测试后的数据清理 |
| `thread_init()` | 线程初始化（连接数据库等） |
| `thread_done()` | 线程结束时的清理 |

### 常用 Lua API

```lua
sysbench.rand.uniform(1, 1000)      -- 随机整数
sysbench.rand.special(1, 1000)      -- 特殊分布随机数
db_query("SELECT ...")               -- 执行 SQL
db_prepare("SELECT ... WHERE id = ?")-- 预编译语句
```

---

## 速查总结

```
┌──────────────────────────────────────────────────────────────┐
│                    sysbench 七大测试能力                       │
├────────────┬──────────────────────┬──────────────────────────┤
│  测试模块   │      测试对象         │      核心指标             │
├────────────┼──────────────────────┼──────────────────────────┤
│  cpu       │  CPU 整数运算能力     │  events per second       │
│  fileio    │  磁盘 I/O 读写性能    │  IOPS / 吞吐量 / 延迟    │
│  threads   │  调度器效率           │  events per second       │
│  memory    │  内存带宽和延迟       │  MiB/sec                 │
│  mutex     │  线程锁竞争性能       │  total time              │
│  OLTP      │  数据库事务性能       │  TPS / QPS / P95 延迟     │
│  Lua 自定义 │  任意自定义场景       │  按需定义                 │
└────────────┴──────────────────────┴──────────────────────────┘
```

如果你有具体的测试场景（比如对比两台服务器的性能、压测某个数据库配置等），可以告诉我，我帮你设计具体的测试方案。
