---
title: PostgreSQL 部署架构选型指南
date: 2026-08-15 09:15:00
tags:
  - PostgreSQL
  - 架构
categories:
  - PostgreSQL SRE
---

PostgreSQL 架构选型需结合业务 SLA、读写比例与团队运维能力。

## 常见架构

| 架构 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| 单机 | 开发/测试、低 SLA | 简单 | 无 HA |
| 主从流复制 | 读写分离、RPO 分钟级 | 成熟、生态好 | 需外部 HA 组件 |
| Patroni + etcd | 生产 HA | 自动 failover | 组件多 |
| 云 RDS/Aurora PG | 免运维 | 托管备份/监控 | 成本、定制受限 |
| Citus 分布式 | 超大规模写入/分析 | 水平扩展 | 运维复杂 |

## 读写分离方案

```
App → PgBouncer → HAProxy → Primary（写）
                         → Standby（读，hot_standby）
```

- **同步复制**：RPO=0，写延迟增加
- **异步复制**：RPO 取决于 WAL 积压
- **quorum sync**：多数派确认，平衡一致性与性能

## 选型决策树

```
QPS < 5000 且数据 < 500GB？
  ├─ 是 → 主从 + Patroni
  └─ 否 → 是否需跨节点 JOIN？
           ├─ 是 → Citus 或应用层分片
           └─ 否 → 读副本扩展 + 连接池
```

## 版本选择

- 生产推荐 **PostgreSQL 16/17** LTS 社区版
- 扩展兼容性：PostGIS、pgvector、TimescaleDB 需提前验证

## 部署形态

| 形态 | 场景 |
|------|------|
| 裸机/VM | 高性能、可控 |
| Docker | 开发/CI |
| K8s Operator | 云原生、弹性 |
| 托管云 | 小团队、快速上线 |

架构文档应包含：拓扑图、failover 流程、RPO/RTO、连接串变更方式。
