---
title: sysbench 基准测试工具详解
date: 2026-09-07 23:15:00
tags:
  - MySQL
  - sysbench
  - 性能测试
  - Linux
categories:
  - MySQL
---

## sysbench 的主要测试模块

| 模块 | 用途 |
|---|---|
| **cpu** | CPU 计算性能（默认素数运算） |
| **memory** | 内存读写带宽和延迟 |
| **threads** | 线程调度和同步性能 |
| **mutex** | 互斥锁竞争性能 |
| **fileio** | 文件 I/O 吞吐和延迟 |
| **oltp** | 数据库 OLTP 模拟测试（最常用） |

## 典型使用流程（以 MySQL OLTP 为例）

```bash
# 1. 准备测试数据
sysbench oltp_read_write \
  --mysql-host=127.0.0.1 \
  --mysql-user=root \
  --mysql-password=xxx \
  --mysql-db=sbtest \
  --tables=10 \
  --table-size=1000000 \
  prepare

# 2. 执行测试
sysbench oltp_read_write \
  --threads=16 \
  --time=300 \
  --report-interval=10 \
  run

# 3. 清理测试数据
sysbench oltp_read_write \
  --mysql-host=127.0.0.1 \
  --mysql-user=root \
  --mysql-password=xxx \
  --mysql-db=sbtest \
  cleanup
```

## 几个实用参数

- `--threads` — 并发线程数
- `--time` — 测试持续时间（秒）
- `--report-interval` — 每隔多少秒输出一次中间结果
- `--percentile=99` — 输出第 99 百分位延迟（P99）
- `--histogram` — 输出延迟直方图

## 版本提示

sysbench 有两个大版本：
- **0.4.x** — 老版本，OLTP 测试脚本内置
- ****1.0+**** — 新版本改用 **Lua 脚本驱动**，灵活度大幅提升，OLTP 测试在 `oltp_read_write`、`oltp_read_only` 等命令中

现在推荐使用 **1.0+** 版本，功能更完善，Lua 脚本也方便自定义测试场景。

---

你是在做数据库性能评估、服务器选型对比，还是有具体的问题想讨论？
