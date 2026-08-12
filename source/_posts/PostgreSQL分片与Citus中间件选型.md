---
title: PostgreSQL 分片与 Citus 中间件选型
date: 2026-08-15 12:30:00
tags:
  - PostgreSQL
  - Citus
  - 分片
categories:
  - PostgreSQL SRE
---

单机 PostgreSQL 有上限，超大规模需分片或分布式扩展。

## 何时分片

| 信号 | 阈值参考 |
|------|----------|
| 单库 > 2TB | 考虑分片 |
| 写入 QPS > 10k | 写入瓶颈 |
| 索引/表 bloat 难维护 | 水平拆分 |
| 跨地域低延迟 | 地理分片 |

## 分片方案对比

| 方案 | 特点 | 适用 |
|------|------|------|
| 应用层分片 | 灵活、复杂 | 强定制 |
| Citus | PG 原生扩展 | OLTP + 实时分析 |
| 外部中间件（ShardingSphere） | 多 DB 支持 | 混合栈 |
| FDW + 分区 | 轻量 | 只读聚合 |

## Citus 架构

```
Coordinator → Worker 1（shard 0-31）
           → Worker 2（shard 32-63）
```

```sql
CREATE EXTENSION citus;
SELECT citus_add_node('worker1', 5432);
SELECT citus_add_node('worker2', 5432);

CREATE TABLE events (
  id bigserial,
  tenant_id int,
  payload jsonb,
  created_at timestamptz
);
SELECT create_distributed_table('events', 'tenant_id');
```

## 分片键选择

- 高基数、查询常带：`tenant_id`、`user_id`
- 避免热点：均匀分布
- 跨 shard JOIN 代价高，尽量 co-location

## 应用层分片（简化）

```
user_id % 4 → pg-shard-0 ~ pg-shard-3
```

中间件或 SDK 路由，全局 ID 用 Snowflake。

## SRE 运维差异

| 项 | 单机 | 分片 |
|----|------|------|
| 备份 | 单点 | 每 shard + coordinator |
| 迁移 | pg_upgrade 一次 | 协调多节点 |
| 监控 | 单实例 | 聚合 + 单 shard 告警 |
| DDL | 直接执行 | Citus 需 propagate |

## 检查清单

- [ ] 分片键不可随意变更
- [ ] 跨 shard 事务尽量避免
- [ ] rebalance 计划（Citus rebalance）
- [ ] 容量按 shard 独立规划

**先垂直扩展 + 读副本**，确认瓶颈后再分片，避免过早复杂化。
