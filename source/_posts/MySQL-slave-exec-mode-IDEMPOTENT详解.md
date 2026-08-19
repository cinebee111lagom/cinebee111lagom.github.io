---
title: MySQL slave_exec_mode IDEMPOTENT详解
date: 2026-09-08 07:30:00
tags:
  - MySQL
  - 主从复制
  - slave_exec_mode
  - DBA
categories:
  - MySQL
---

## 基本概念

`slave_exec_mode` 是 MySQL 复制中的一个服务器系统变量，控制 **slave（从库）SQL 线程** 在执行复制事件时遇到错误的处理方式。它有两个可选值：

| 值 | 说明 |
|---|---|
| `STRICT` | 默认值（MySQL 8.0 之前某些版本），遇到错误立即停止复制 |
| `IDEMPOTENT` | 以幂等模式执行，忽略某些错误继续运行 |

## IDEMPOTENT 模式下忽略的错误

设置为 `IDEMPOTENT` 后，SQL 线程会自动跳过以下两类问题：

### 1. 主键/唯一键冲突（1062 / ER_DUP_ENTRY）
```
INSERT → 目标行已存在 → 忽略
```

### 2. 找不到目标行（1032 / ER_KEY_NOT_FOUND）
```
DELETE → 目标行不存在 → 忽略
UPDATE → 目标行不存在 → 忽略
```

简单来说：**"该在的不在，该不在的在了"——统统当没事发生。**

## 典型使用场景

### NDB Cluster（最重要的场景）
```ini
# 在 NDB Cluster 的 SQL 节点上必须设置
[mysqld]
slave_exec_mode = IDEMPOTENT
```

NDB 引擎使用 epoch 同步机制，在节点恢复时可能重新接收已经执行过的事件，导致重复应用。`IDEMPOTENT` 模式避免了因此导致的复制中断。

### 自动故障转移后重建从库
```
Master (M)
  ├── Slave1 (S1) ← 提升为新 Master
  └── Slave2 (S2) ← 切换到 S1 作为新 Master
```
切换过程中可能有部分事务在两个方向上都执行过，幂等模式可以容忍这种重叠。

### pt-table-checksum + pt-table-sync 修复数据后
在数据修复后重新建立复制链路时使用。

## 设置方式

```sql
-- 动态设置（运行时生效，无需重启）
SET GLOBAL slave_exec_mode = 'IDEMPOTENT';

-- 查看当前值
SHOW VARIABLES LIKE 'slave_exec_mode';

-- 恢复严格模式
SET GLOBAL slave_exec_mode = 'STRICT';
```

配置文件方式：
```ini
[mysqld]
slave_exec_mode = IDEMPOTENT
```

## 重要注意事项与风险

### 不是万能的
它 **只** 忽略 1032 和 1062 错误。其他复制错误（如表不存在、列不匹配等）仍然会导致复制停止。

### 可能掩盖数据不一致

这是最大的隐患。它不解决根本问题，只是让复制不停：

```
实际状态：主库有 row A，从库没有 row A
主库 DELETE row A → 从库尝试 DELETE → row 不存在 → 忽略
结果：两边都没有 row A ✓ （这次碰巧没问题）

实际状态：主库没有 row B，从库有 row B
主库 INSERT row B → 从库尝试 INSERT → 主键冲突 → 忽略
结果：从库的 row B 是旧版本的脏数据 ✗
```

**幂等模式让复制"看起来正常"，但数据可能已经不一致了。**

### 建议搭配的措施
```
┌─────────────────────────────────────────┐
│  使用 IDEMPOTENT 模式时的配套策略        │
├─────────────────────────────────────────┤
│  1. 定期用 pt-table-checksum 校验数据   │
│  2. 开启 GTID 模式辅助跟踪一致性        │
│  3. 问题解决后尽快切回 STRICT            │
│  4. 记录 warning 日志并监控              │
│  5. 不要在常规异步复制中长期使用          │
└─────────────────────────────────────────┘
```

## 与 GTID 的关系

在 **GTID 模式** 下，`slave_exec_mode = IDEMPOTENT` 的行为：

- 已执行过的 GTID 事务会被 `SERVER_AUTO_SKIP` 直接跳过（这是 GTID 本身的机制，不依赖 `slave_exec_mode`）
- `IDEMPOTENT` 额外处理的是：GTID 不同但碰巧操作了同一行的冲突情况（如 failover 过程中产生的）

## 总结

```
slave_exec_mode = IDEMPOTENT
    ├── 本质：容错开关，不是修复工具
    ├── 核心：忽略重复插入 + 缺失删除/更新
    ├── 必需：NDB Cluster 环境
    ├── 可选：故障转移 / 数据修复过渡期
    └── 风险：掩盖数据漂移，需定期校验
```

一句话概括：**它让复制不轻易中断，但你应该把这当作临时手段而非长期策略。**
