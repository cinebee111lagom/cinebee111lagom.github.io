---
title: MySQL 主从复制详解
date: 2026-09-08 05:30:00
tags:
  - MySQL
  - 主从复制
  - GTID
  - DBA
categories:
  - MySQL
---

---

## 一、传统 Binlog 主从复制

### 1. 基本原理

```
┌──────────────┐         ┌──────────────┐
│   Master     │         │   Slave      │
│              │         │              │
│  ① 写操作    │         │              │
│      │       │         │              │
│      ▼       │         │              │
│  Binlog      │─────▶──│  ② IO线程    │
│              │  网络    │  拉取binlog   │
│              │         │      │       │
│              │         │      ▼       │
│              │         │  Relay Log   │
│              │         │  (中继日志)   │
│              │         │      │       │
│              │         │      ▼       │
│              │         │  ③ SQL线程   │
│              │         │  重放SQL      │
│              │         │      │       │
│              │         │      ▼       │
│              │         │  数据一致     │
└──────────────┘         └──────────────┘
```

### 2. 核心三线程

| 线程 | 位置 | 职责 |
|------|------|------|
| **Binlog Dump Thread** | Master | 接收 Slave 的请求，读取 binlog 并发送给 Slave |
| **I/O Thread** | Slave | 连接 Master，接收 binlog 事件，写入本地 Relay Log |
| **SQL Thread** | Slave | 读取 Relay Log，将事件重放到 Slave 数据库 |

### 3. 复制模式

```
异步复制（默认）
─────────────────
Master 写入 binlog → 返回客户端成功
     （不等 Slave 确认）
     风险：Master 宕机可能丢数据


半同步复制（Semi-Sync）
────────────────────────
Master 写入 binlog → 至少 1 个 Slave 写入 Relay Log 并 ACK → 才返回客户端成功
     保障：至少一个 Slave 有数据
     代价：延迟增加，性能下降


全同步复制
──────────
所有 Slave 都确认后才返回
     几乎不用，性能太差
```

### 4. 配置步骤

**Master 端：**

```ini
# my.cnf
[mysqld]
server-id        = 1
log-bin           = mysql-bin
binlog-format     = ROW          # 推荐 ROW 格式
expire-logs-days  = 7
```

```sql
-- 创建复制用户
CREATE USER 'repl'@'%' IDENTIFIED BY 'repl_password';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;

-- 查看 Master 状态（记录下 File 和 Position）
SHOW MASTER STATUS;
```

```
+------------------+----------+
| File             | Position |
+------------------+----------+
| mysql-bin.000003 |      785 |
+------------------+----------+
```

**Slave 端：**

```ini
# my.cnf
[mysqld]
server-id        = 2
relay-log         = relay-bin
read-only         = ON
```

```sql
-- 指定 Master 信息（基于文件 + 位置）
CHANGE MASTER TO
  MASTER_HOST     = '192.168.1.100',
  MASTER_PORT     = 3306,
  MASTER_USER     = 'repl',
  MASTER_PASSWORD = 'repl_password',
  MASTER_LOG_FILE = 'mysql-bin.000003',
  MASTER_LOG_POS  = 785;

-- 启动复制
START SLAVE;

-- 查看状态
SHOW SLAVE STATUS\G
```

**关键检查项：**
```
Slave_IO_Running: Yes       ← 必须都是 Yes
Slave_SQL_Running: Yes      ← 必须都是 Yes
Seconds_Behind_Master: 0    ← 延迟秒数，0 表示无延迟
```

### 5. Binlog 格式对比

```
┌─────────────┬──────────────────────────────────────────┐
│   Statement │  记录原始 SQL 语句                        │
│             │  INSERT INTO t VALUES(1, 'test')          │
│             │  缺点：NOW()、UUID() 等函数结果不一致       │
├─────────────┼──────────────────────────────────────────┤
│   Row       │  记录每行数据的变更（推荐）                 │
│             │  行变更前的值 → 行变更后的值                 │
│             │  优点：数据一致性最好                       │
│             │  缺点：日志量大                            │
├─────────────┼──────────────────────────────────────────┤
│   Mixed     │  默认 Statement，不安全时自动切 Row        │
│             │  折中方案，用得较少                         │
└─────────────┴──────────────────────────────────────────┘
```

### 6. 传统复制的痛点

```
❌ 依赖 binlog 文件名 + 偏移量（Position）
   → 切换主从时需要手动指定新 Master 的 File 和 Position
   → 容易出错，操作复杂

❌ 主从切换困难
   → Master 宕机后，选哪个 Slave 提升为新 Master？
   → 提升后其他 Slave 如何指向新 Master？
   → 手动操作步骤多、风险大

❌ 无法自动追踪复制进度
   → Position 在不同节点上含义不同
   → 难以判断 Slave 是否已经追上 Master 的某个事务
```

---

## 二、GTID 主从复制

### 1. 什么是 GTID

```
GTID = Global Transaction Identifier
       全局事务标识符

格式：server_uuid:transaction_id

示例：3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5

含义：UUID 为 3E11FA47-... 的服务器上执行的第 1 到第 5 个事务
```

**核心特点：**
- 每个事务在**整个复制拓扑中唯一**
- 不再依赖 binlog 文件名 + 偏移量
- MySQL 5.6 引入，**MySQL 5.7 推荐使用**

### 2. 复制流程对比

```
传统复制：
  "请从 mysql-bin.000003 的第 785 个字节开始给我数据"
  → 位置绑定，不够智能

GTID复制：
  "请给我 3E11FA47-...:6 开始之后的所有事务"
  → 自动定位，不关心具体在哪个 binlog 文件的哪个位置
```

### 3. GTID 集合

```
GTID Set 的表示方式：

3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5
    │                                    │
    └── Server UUID                      └── 事务 1,2,3,4,5

多段表示：
3E11FA47-71CA-11E1-9E33-C80AA9429562:1-3:5-7
    → 事务 1,2,3,5,6,7（跳过了4）

多个 Server：
server1_uuid:1-5, server2_uuid:1-3
    → server1 的 1-5 号事务 + server2 的 1-3 号事务
```

### 4. 配置步骤

**Master 端：**

```ini
# my.cnf
[mysqld]
server-id        = 1
log-bin           = mysql-bin
binlog-format     = ROW
gtid-mode         = ON                    # 开启 GTID
enforce-gtid-consistency = ON             # 强制 GTID 一致性
expire-logs-days  = 7
```

```sql
CREATE USER 'repl'@'%' IDENTIFIED BY 'repl_password';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
```

**Slave 端：**

```ini
# my.cnf
[mysqld]
server-id        = 2
relay-log         = relay-bin
gtid-mode         = ON
enforce-gtid-consistency = ON
log-slave-updates = ON                    # 将复制的事务也写入自己的 binlog（级联复制需要）
read-only         = ON
```

```sql
-- 配置 GTID 自动定位
CHANGE MASTER TO
  MASTER_HOST     = '192.168.1.100',
  MASTER_PORT     = 3306,
  MASTER_USER     = 'repl',
  MASTER_PASSWORD = 'repl_password',
  MASTER_AUTO_POSITION = 1;              -- 关键：自动定位

START SLAVE;
SHOW SLAVE STATUS\G
```

**重点查看：**
```
Retrieved_Gtid_Set: 3E11FA47-...:1-10     -- 已拉取的 GTID
Executed_Gtid_Set:  3E11FA47-...:1-10     -- 已执行的 GTID
Auto_Position:      1                      -- 自动定位开启
```

### 5. GTID 复制原理

```
┌──────────────────────────────────────────────────────────────┐
│                       Slave 连接 Master                      │
│                                                              │
│  ① Slave 发送自己的 Executed_Gtid_Set 给 Master             │
│     "我已经执行了 server1:1-5, server2:1-3"                   │
│                                                              │
│  ② Master 计算差集                                            │
│     全部事务 GTID Set - Slave 已执行的 GTID Set = 差集         │
│     "你需要 server1:6-10, server2:4-7"                       │
│                                                              │
│  ③ Master 发送差集对应的 binlog 事件                           │
│     Slave 的 IO 线程接收并写入 Relay Log                      │
│                                                              │
│  ④ Slave 的 SQL 线程重放，更新自己的 Executed_Gtid_Set        │
└──────────────────────────────────────────────────────────────┘
```

### 6. GTID 的重大优势 — 主从切换

```
场景：Master (M) 宕机，需要将 Slave1 (S1) 提升为新 Master

传统复制的痛苦操作：
──────────────────────
1. 在 S1 上执行 SHOW MASTER STATUS 记录 File 和 Position
2. 其他 Slave (S2, S3) 手动执行 CHANGE MASTER TO
   CHANGE MASTER TO MASTER_LOG_FILE='...', MASTER_LOG_POS=...;
3. 每一步都可能出错

GTID 的优雅操作：
──────────────────
1. 将 S1 提升为 Master（去掉 read-only）
2. 其他 Slave 执行：
   CHANGE MASTER TO MASTER_HOST='S1', MASTER_AUTO_POSITION=1;
   START SLAVE;
3. 完成！自动从正确位置开始复制
```

```
┌─────────┐          ┌─────────┐          ┌─────────┐
│   S2    │          │  S1新M  │          │   S3    │
│         │◀────────│         │─────────▶│         │
│ AUTO_POS│          │ GTID    │          │ AUTO_POS│
│    =1   │          │ Enabled │          │    =1   │
└─────────┘          └─────────┘          └─────────┘

    自动发现差异 → 自动从正确位置复制 → 无需手动计算 Position
```

---

## 三、全面对比

```
┌──────────────────┬─────────────────────┬────────────────────────┐
│     对比维度      │   传统 Binlog 复制   │     GTID 复制           │
├──────────────────┼─────────────────────┼────────────────────────┤
│ 定位方式          │ File + Position     │ server_uuid:txn_id     │
│                  │ (文件名+偏移量)      │ (全局唯一事务ID)        │
├──────────────────┼─────────────────────┼────────────────────────┤
│ 主从切换          │ 手动、复杂、易出错    │ 自动定位，简单可靠       │
├──────────────────┼─────────────────────┼────────────────────────┤
│ 故障恢复          │ 需要人工计算位点      │ 自动跳过已执行事务       │
├──────────────────┼─────────────────────┼────────────────────────┤
│ 多源复制          │ 支持但配置复杂        │ 天然支持                │
├──────────────────┼─────────────────────┼────────────────────────┤
│ 复制状态追踪      │ 不直观              │ SHOW SLAVE STATUS 可直接 │
│                  │                     │ 看到已执行的 GTID 集合   │
├──────────────────┼─────────────────────┼────────────────────────┤
│ 跳过事务          │ SET GLOBAL          │ GTID_NEXT + 空事务      │
│                  │ sql_slave_skip=1    │ (更精确，更安全)         │
├──────────────────┼─────────────────────┼────────────────────────┤
│ 限制              │ 无                  │ 不能使用                │
│                  │                     │ CREATE TABLE ... SELECT │
│                  │                     │ 不能在同一事务中同时     │
│                  │                     │ 更新事务和非事务引擎表   │
├──────────────────┼─────────────────────┼────────────────────────┤
│ MySQL 版本        │ 3.23+               │ 5.6+ 引入，5.7+ 推荐    │
├──────────────────┼─────────────────────┼────────────────────────┤
│ 学习成本          │ 低                  │ 稍高                    │
└──────────────────┴─────────────────────┴────────────────────────┘
```

### GTID 限制详情

```sql
-- ❌ 不允许
CREATE TABLE t2 SELECT * FROM t1;

-- 需改写为：
CREATE TABLE t2 LIKE t1;
INSERT INTO t2 SELECT * FROM t1;
```

---

## 四、GTID 跳过事务（实战）

```sql
-- 传统方式跳过（粗糙）
STOP SLAVE;
SET GLOBAL sql_slave_skip_counter = 1;
START SLAVE;

-- GTID 跳过（精确到单个事务）
STOP SLAVE;
SET GTID_NEXT = 'server_uuid:100';   -- 指定要跳过的事务 GTID
BEGIN; COMMIT;                         -- 注入空事务，标记为已执行
SET GTID_NEXT = 'AUTOMATIC';          -- 恢复自动模式
START SLAVE;
```

---

## 五、架构演进路线

```
传统异步复制（最基础）
       │
       ▼
半同步复制（防丢数据）
       │
       ▼
GTID 复制（简化管理）
       │
       ▼
GTID + 半同步（生产推荐）
       │
       ▼
MGR / InnoDB Cluster（MySQL 8.0+ 终极方案）
```

**生产环境建议**：MySQL 5.7+ 优先使用 **GTID + 半同步复制**，兼顾数据安全和运维便利性。MySQL 8.0 可考虑 MGR（MySQL Group Replication）。
