---
title: MySQL Group Replication MGR常见问题与处理
date: 2026-09-08 04:15:00
tags:
  - MySQL
  - MGR
  - Group Replication
  - DBA
categories:
  - MySQL
---

---

## 一、节点状态异常

### 1. 节点变为 `ERROR` 或 `UNREACHABLE`

**常见原因：**
- 网络抖动或超时（节点间心跳丢失）
- 节点长时间 GC（垃圾回收）或磁盘 I/O 阻塞
- 节点执行了不兼容的事务

**排查步骤：**
```sql
-- 查看组成员状态
SELECT * FROM performance_schema.replication_group_members;

-- 查看成员连接状态
SELECT * FROM performance_schema.replication_group_member_stats\G

-- 查看错误日志
SHOW VARIABLES LIKE 'log_error';
```

**处理方式：**
```sql
-- 节点仍在组中但状态异常，先将其移除
STOP GROUP_REPLICATION;

-- 检查并修复问题后重新加入
SET GLOBAL group_replication_start_on_boot = OFF;
START GROUP_REPLICATION;
```

如果节点无法自动恢复，需要做 **全量数据重建**：
```bash
# 方式一：使用 Clone 插件（推荐，MySQL 8.0.17+）
INSTALL PLUGIN clone SONAME 'mysql_clone.so';
CLONE INSTANCE FROM 'donor_user'@'donor_host':3306
  IDENTIFIED BY 'password';

# 方式二：Xtrabackup 物理备份恢复
```

---

## 2. 脑裂 / 网络分区

**现象：** 组内出现两个独立的子组，各自选举 Primary

**预防配置：**
```ini
# my.cnf
# 至少需要多少个节点才允许写入（防止少数派脑裂）
group_replication_consistency = BEFORE_ON_PRIMARY_FAILOVER
# 设置超时踢出阈值
group_replication_member_expel_timeout = 5     # 5秒后驱逐（默认5s，MySQL 8.0.13+）
group_replication_unreachable_majority_timeout = 10  # 多数派不可达超时
```

**处理方式：**
- 确认网络恢复后，少数派节点会自动尝试重新加入
- 如果少数派已经产生脏数据，需清除该节点数据后重新以新成员加入

---

## 二、写入冲突

### 1. 事务冲突回滚

**现象：**
```
ERROR 3101 (HY000): Plugin instructed the server to rollback the current transaction.
```

**原因：** 多主模式（Multi-Primary）下，并发事务修改同一行数据，认证失败导致回滚。

**处理方式：**
```sql
-- 方式一：开启冲突检测回退重试（应用层重试）
SET GLOBAL group_replication_transaction_size_limit = 150000000;  -- 调大冲突检测阈值

-- 方式二：使用单主模式（推荐，避免冲突）
-- 启动时指定单主模式
SET GLOBAL group_replication_single_primary_mode = TRUE;
```

### 2. 认证冲突日志监控
```sql
-- 查看冲突/回滚统计
SELECT * FROM performance_schema.replication_group_member_stats
WHERE CHANNEL_NAME = 'group_replication_applier'\G

-- 关注以下字段：
-- COUNT_TRANSACTIONS_LOCAL_ROLLBACK
-- COUNT_TRANSACTIONS_REMOTE_APPLIER
-- COUNT_CONFLICTS_DETECTED
```

---

## 三、数据一致性问题

### 1. 读写分离读到旧数据

**现象：** 从节点读到的数据滞后于主节点

**处理方式：**
```sql
-- 设置一致性级别（确保读到最新数据）
SET SESSION group_replication_consistency = 'AFTER';

-- AFTER：等到所有已提交事务在本节点应用完毕后再执行读
-- BEFORE：在执行前等待本节点追上
-- BEFORE_ON_PRIMARY_FAILOVER：主节点故障转移时，新主等待数据一致后才接受读
```

### 2. 数据不一致检测（MySQL 8.0.21+）

```sql
-- 启用数据一致性检查
SET GLOBAL group_replication_consistency = 'BEFORE_ON_PRIMARY_FAILOVER';

-- 使用 mysql shell 检查
util.checkForServerUpgrade();

-- 或者使用 pt-table-checksum
pt-table-checksum --replicate=percona.checksums h=host,P=3306
```

---

## 四、性能问题

### 1. 认证（Certification）瓶颈

**现象：** 所有写入都经过主节点认证后广播到组，认证过程成为瓶颈

**优化配置：**
```ini
# 增大通信缓冲区
group_replication_communication_max_message_size = 10485760   # 10MB

# 压缩组通信
group_replication_compression_threshold = 1000000            # 超过1MB压缩

# 流控参数调优
group_replication_flow_control_mode = QUOTA                  # 按配额流控
group_replication_flow_control_certifier_threshold = 25000   # 认证队列阈值
group_replication_flow_control_applier_threshold = 25000     # 应用队列阈值
```

### 2. 流控导致写入骤降

**现象：** 延迟大的从节点触发流控，整个组写入降速

```sql
-- 查看流控状态
SHOW STATUS LIKE 'group_replication_flow%';

-- 临时关闭流控（不推荐生产使用）
SET GLOBAL group_replication_flow_control_mode = 'DISABLED';

-- 推荐：调整流控参数
SET GLOBAL group_replication_flow_control_certifier_threshold = 50000;
SET GLOBAL group_replication_flow_control_applier_threshold = 50000;
```

---

## 五、集群搭建 / 成员加入失败

### 1. 新节点加入失败

**常见报错及处理：**

| 报错 | 原因 | 处理 |
|------|------|------|
| `The member has a higher ...` | GTID 集合冲突 | 检查 `gtid_executed`，清理冲突数据 |
| `Unable to connect to bootstrap group` | 网络不通 / 端口未开放 | 检查 `group_replication_group_seeds` 配置和防火墙 |
| `This server is not able to reach a majority of members` | 节点数不足 | 确保至少 `(n/2 + 1)` 个节点可达 |
| `Table ... does not use the InnoDB storage engine` | 存在非 InnoDB 表 | 所有表必须是 InnoDB |

### 2. 成员自动重启 Group Replication 失败

```ini
# my.cnf 确保正确配置
group_replication_start_on_boot = OFF   # 建议手动控制，避免循环失败

# 加入时显式指定
SET GLOBAL group_replication_group_seeds = 'host1:33061,host2:33061,host3:33061';
SET GLOBAL group_replication_local_address = 'host1:33061';
```

---

## 六、日志与监控

### 关键监控指标

```sql
-- 组成员状态
SELECT MEMBER_ID, MEMBER_HOST, MEMBER_PORT, MEMBER_STATE, MEMBER_ROLE
FROM performance_schema.replication_group_members;

-- 事务统计
SELECT
  COUNT_TRANSACTIONS_IN_QUEUE        AS pending_cert,      -- 等待认证
  COUNT_TRANSACTIONS_CHECKED         AS certified,         -- 已认证
  COUNT_TRANSACTIONS_LOCAL_ROLLBACK  AS local_rollback,    -- 本地回滚
  COUNT_TRANSACTIONS_REMOTE_APPLIER  AS remote_applied     -- 远程已应用
FROM performance_schema.replication_group_member_stats
WHERE CHANNEL_NAME='group_replication_applier'\G
```

### 自动化告警脚本（核心逻辑）

```bash
#!/bin/bash
# 检查成员状态，非 ONLINE 即告警
STATE=$(mysql -Nse "SELECT MEMBER_STATE FROM performance_schema.replication_group_members WHERE MEMBER_HOST='$(hostname)';")
if [ "$STATE" != "ONLINE" ]; then
    echo "MGR node state is $STATE" | mail -s "MGR Alert" admin@example.com
fi

# 检查是否有超过阈值的认证队列积压
PENDING=$(mysql -Nse "SELECT COUNT_TRANSACTIONS_IN_QUEUE FROM performance_schema.replication_group_member_stats WHERE CHANNEL_NAME='group_replication_applier';")
if [ "$PENDING" -gt 10000 ]; then
    echo "MGR cert queue backlog: $PENDING" | mail -s "MGR Queue Alert" admin@example.com
fi
```

---

## 七、最佳实践速查

| 项目 | 建议 |
|------|------|
| **模式** | 生产环境推荐 Single-Primary，多主模式仅用于特殊场景 |
| **节点数** | 至少 3 个（奇数），仲裁依赖多数派 |
| **网络** | 节点间延迟 < 10ms，建议同机房/同可用区 |
| **超时** | `member_expel_timeout` 根据网络质量调大（5~15s） |
| **一致性** | 关键读设置 `AFTER` 或 `BEFORE_ON_PRIMARY_FAILOVER` |
| **存储引擎** | 只用 InnoDB，关闭 `log_bin` 的非 InnoDB 日志 |
| **GTID** | 必须开启 `gtid_mode=ON`，`enforce_gtid_consistency=ON` |
| **备份** | 定期备份，优先从 Secondary 节点备份 |

---

如果你有具体的报错信息或场景，可以贴出来，我帮你针对性分析。
