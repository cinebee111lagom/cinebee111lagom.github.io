---
title: MySQL MGR 组复制高可用部署
date: 2026-08-14 09:45:00
tags:
  - MySQL
  - MGR
categories:
  - MySQL SRE
---

**MySQL Group Replication（MGR）** 提供基于 Paxos 的多主/单主复制与自动 membership 管理。

## 节点要求

- 至少 **3 节点**（容忍 1 故障）
- 同版本 MySQL 8.0+
- 低延迟内网（< 10ms 推荐）

## 关键配置

```ini
plugin_load_add = 'group_replication.so'
group_replication_group_name = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
group_replication_start_on_boot = OFF
group_replication_local_address = "10.0.1.11:33061"
group_replication_group_seeds = "10.0.1.11:33061,10.0.1.12:33061,10.0.1.13:33061"
group_replication_single_primary_mode = ON
```

## -bootstrap 首节点

```sql
SET GLOBAL group_replication_bootstrap_group=ON;
START GROUP_REPLICATION;
SET GLOBAL group_replication_bootstrap_group=OFF;
```

其余节点 `START GROUP_REPLICATION;`

## 验证

```sql
SELECT * FROM performance_schema.replication_group_members;
-- STATE: ONLINE, ROLE: PRIMARY/SECONDARY
```

## MGR vs 传统主从

| | MGR | 异步主从 |
|---|-----|----------|
| 一致性 | 认证后提交 | 可能丢数据 |
| 自动选主 | ✅ | 需 Orchestrator |
| 性能开销 | 略高 | 低 |
| 运维复杂度 | 高 | 中 |

## 注意事项

- 大事务易触发 flow control
- 不支持 MyISAM 表
- 跨机房部署需评估 RT 对 commit 延迟影响

MGR 适合**强一致、自动 failover** 的核心 OLTP 库。
