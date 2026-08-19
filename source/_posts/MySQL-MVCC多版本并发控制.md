---
title: MySQL MVCC 多版本并发控制
date: 2026-09-08 03:45:00
tags:
  - MySQL
  - MVCC
  - InnoDB
  - 事务
categories:
  - MySQL
---

## 一句话本质

MVCC 的核心思想：**读不阻塞写，写不阻塞读**。通过保存数据的多个历史版本，让不同事务看到的数据"快照"各不相同，从而实现并发读写互不干扰。

---

## 一、为什么需要 MVCC

没有 MVCC 时，并发场景下只有两条路：

| 方案 | 问题 |
|------|------|
| 全局加锁 | 读写互斥，并发度极低 |
| 读写都不加锁 | 脏读、不可重复读、幻读全来了 |

MVCC 是一种 **折中方案**：写操作仍需要加锁（行锁），但 **读操作通过读取历史版本来避免加锁**。

---

## 二、实现基础：三个隐藏机制

### 1. 隐藏字段

InnoDB 每行数据背后附加了几个隐藏列：

```
| DB_TRX_ID | DB_ROLL_PTR | DB_ROW_ID |
```

| 字段 | 含义 |
|------|------|
| **DB_TRX_ID** | 最近修改该行的事务 ID |
| **DB_ROLL_PTR** | 回滚指针，指向 undo log 中该行的上一个版本 |
| **DB_ROW_ID** | 隐藏主键（无显式主键时自动生成） |

通过 `DB_ROLL_PTR`，同一行数据的多个版本串成一条 **版本链**：

```
当前行 [TRX_ID=103] ──ROLL_PTR──▶ undo log [TRX_ID=101] ──▶ undo log [TRX_ID=98] ──▶ ...
```

### 2. Undo Log（回滚日志）

Undo Log 就是存储这些历史版本的地方：

- **Insert undo log**：事务回滚时删除该行即可
- **Update undo log**：记录旧值，供回滚和 MVCC 读取

> 当没有任何事务再需要某版本时，由 **Purge 线程**负责清理。

### 3. ReadView（读视图）

ReadView 是 MVCC 的 **决策核心**，它在某一时刻生成一个"快照"，定义了当前事务 **能看到哪些版本**。

ReadView 包含四个关键字段：

```
┌─────────────────────────────────────────────┐
│                 ReadView                     │
│                                             │
│  m_ids        : 当前活跃（未提交）事务 ID 列表   │
│  min_trx_id   : m_ids 中最小值               │
│  max_trx_id   : 系统下一个要分配的事务 ID       │
│  creator_trx_id: 创建该 ReadView 的事务 ID    │
└─────────────────────────────────────────────┘
```

---

## 三、可见性判断规则

对版本链中的某个版本，其 `DB_TRX_ID` 与 ReadView 对比：

```
                    DB_TRX_ID
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
    < min_trx_id   在 m_ids 中    ≥ max_trx_id
          │         │                  │
       ✅ 可见     ❌ 不可见         ❌ 不可见
     (事务已提交)  (事务还活跃)     (事务在快照后创建)
```

如果当前版本不可见，就沿着 **undo log 版本链** 往前找，直到找到一个可见版本或链尾。

---

## 四、RC 与 RR 的核心区别

**区别仅在于 ReadView 的生成时机不同：**

| 隔离级别 | ReadView 生成时机 | 效果 |
|---------|-----------------|------|
| **READ COMMITTED (RC)** | 每次 SELECT 都生成一个新的 ReadView | 能读到其他事务已提交的最新数据 |
| **REPEATABLE READ (RR)** | 事务中第一次 SELECT 时生成，后续复用 | 整个事务期间看到的数据一致（快照读） |

### 示例对比

```
事务A (TRX_ID=100)                事务B (TRX_ID=101)
─────────────────                ─────────────────
BEGIN;                           BEGIN;
SELECT name FROM t WHERE id=1;
  → ReadView_1 创建               UPDATE t SET name='B' WHERE id=1;
                                   COMMIT;
SELECT name FROM t WHERE id=1;
  → RC: 新 ReadView → 看到 'B' ✅
  → RR: 复用 ReadView → 看到 'A' ✅
```

这就是 RR 下"可重复读"的实现原理。

---

## 五、两种读方式

### 快照读（Snapshot Read）

普通 SELECT 就是快照读，读取的是 MVCC 版本链中的某个版本，**不加锁**。

```sql
SELECT * FROM user WHERE id = 1;
```

### 当前读（Current Read）

读取数据的 **最新已提交版本**，并且 **加锁**：

```sql
SELECT * FROM user WHERE id = 1 FOR UPDATE;      -- 排他锁
SELECT * FROM user WHERE id = 1 LOCK IN SHARE MODE; -- 共享锁
INSERT / UPDATE / DELETE                           -- 自动加排他锁
```

> **幻读问题的解决**：快照读靠 MVCC 的 ReadView；当前读靠 **Next-Key Lock**（行锁 + 间隙锁）。两者配合才能在 RR 下避免幻读。

---

## 六、完整流程图

```
事务发起 SELECT
       │
       ▼
  是快照读？ ──── 否 ──▶ 当前读（加行锁/间隙锁，读最新版本）
       │
      是
       ▼
  有 ReadView？（RR: 复用 / RC: 新建）
       │
       ▼
  遍历版本链
  ┌──────────────────────────────┐
  │  版本 TRX_ID                  │
  │      │                        │
  │      ▼                        │
  │  < min_trx_id?  ──是──▶ ✅ 可见│
  │      │ 否                     │
  │      ▼                        │
  │  ≥ max_trx_id?  ──是──▶ ❌ 不可见
  │      │ 否                     │
  │      ▼                        │
  │  在 m_ids 中?   ──是──▶ ❌ 不可见
  │      │ 否                     │
  │      ▼                        │
  │  ✅ 可见                      │
  └──────────────────────────────┘
       │
  ❌ 全链不可见 → 返回空
  ✅ 找到可见版本 → 返回该版本数据
```

---

## 七、总结要点

| 要点 | 说明 |
|------|------|
| **核心数据结构** | undo log 版本链 + ReadView |
| **核心作用** | 读不加锁，读写并发 |
| **RC vs RR** | ReadView 创建时机不同（每次 vs 首次） |
| **快照读** | 读历史版本，靠 MVCC |
| **当前读** | 读最新版本，靠行锁 |
| **幻读防治** | MVCC（快照读）+ Next-Key Lock（当前读）共同完成 |
| **版本清理** | Purge 线程根据最老活跃 ReadView 清理过期版本 |

MVCC 是 InnoDB 实现高性能并发的基石 —— 它将"锁"从读路径上移除，用版本链和可见性判断替代，极大提升了数据库的并发吞吐能力。
