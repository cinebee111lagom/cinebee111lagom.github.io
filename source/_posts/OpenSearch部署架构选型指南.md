---
title: OpenSearch 部署架构选型指南
date: 2026-08-20 09:15:00
tags:
  - OpenSearch
  - 架构
categories:
  - OpenSearch SRE
---

OpenSearch 架构选型需结合数据量、查询模式与运维能力。

## 常见架构

| 架构 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| 单节点 | 开发/POC | 简单 | 无 HA |
| 3 节点通用 | 中小规模 | 成本适中 | 角色混合 |
| 角色分离 | 大规模生产 | 性能隔离 | 节点多 |
| 热温冷 | 日志长期保留 | 成本优化 | ISM 运维 |
| 托管 AWS OpenSearch | 免运维 | 集成云生态 | 成本、定制 |

## 节点角色分离（推荐生产）

```
3 × cluster_manager（专用，不存数据）
N × data（热节点，SSD）
M × data（warm/cold，HDD 或 S3）
可选 ingest 节点（预处理）
```

## 选型决策树

```
数据量 < 1TB 且 QPS 低？
  ├─ 是 → 3 data 节点（身兼 cluster_manager）
  └─ 否 → 是否日志 30 天+ 保留？
           ├─ 是 → 热温冷 + ISM
           └─ 否 → 横向扩 data 节点 + 分片 rebalance
```

## 分片规划原则

- 单 shard 建议 **20~50GB**
- primary shard 数创建后不可改（需 reindex）
- 日志按日索引，单索引 2~5 primary

## 存储

| 类型 | 场景 |
|------|------|
| NVMe SSD | 热数据、高写入 |
| EBS gp3/io2 | 云环境 |
| S3（ searchable snapshot） | 冷数据 |

## 版本

- 生产推荐 **OpenSearch 2.x** 最新稳定版
- 与 OpenSearch Dashboards 版本对齐

架构文档应包含：节点拓扑、索引命名规范、ISM 策略、快照仓库、升级路径。
