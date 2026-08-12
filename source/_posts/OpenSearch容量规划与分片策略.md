---
title: OpenSearch 容量规划与分片策略
date: 2026-08-20 12:15:00
tags:
  - OpenSearch
  - 容量规划
categories:
  - OpenSearch SRE
---

容量规划需预估数据增长、写入 QPS、保留天数与分片数量。

## 磁盘估算

```
总磁盘 ≈ 原始数据 × (1 + 副本数) × 1.1（开销）× 保留天数/单日量

例：100GB/天，副本1，保留30天
→ 100 × 2 × 1.1 × 30 ≈ 6.6TB（含 overhead）
```

## 分片策略

| 原则 | 建议 |
|------|------|
| 单 shard 大小 | 20~50GB |
| 单节点 shard 数 | < 1000（调低 max_shards_per_node） |
| 日志索引 | 按日，2~5 primary |
| 搜索索引 | 按容量 shrink |

## 节点数估算

```
data 节点数 ≥ primary_shards / 每节点建议 shard 数
每节点 heap 16GB → 约管 500GB~1TB 数据（视查询负载）
```

## 写入吞吐

| 规模 | 参考 |
|------|------|
| 小型 | 10k docs/s |
| 中型 | 50k docs/s |
| 大型 | 需 dedicated ingest + 多 data |

压测 bulk 确定单集群上限。

## 扩容方式

| 方式 | 场景 |
|------|------|
| 加 data 节点 | 容量/查询 CPU 不足 |
| 加副本 | 读扩展 |
| 新索引 + 别名 | 日志滚动天然扩展 |
| reindex | mapping 变更 |

## 缩容

- 排除节点：`/_cluster/settings` allocation exclude
- 等待 shard 迁走
- shrink 减少 shard

## 容量报告

```
集群：prod-opensearch
节点：6 data × 16GB heap × 1TB disk
索引：450，总数据 3.2TB
日增：120GB
保留：30d ISM
余量：磁盘 42%
结论：2 月后需 +2 data 节点
```

## Checklist

- [ ] 磁盘使用率 < 70%（规划线）
- [ ] 单 shard 大小 review 季度
- [ ] ISM delete 与容量联动
- [ ] 大促前压测

**分片数创建时定死**，容量规划要前置。
