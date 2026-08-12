---
title: OpenSearch 核心概念：Index、Document、Shard
date: 2026-08-19 09:30:00
tags:
  - OpenSearch
  - 概念
categories:
  - OpenSearch 入门
---

理解 Index、Document、Shard 是使用 OpenSearch 的基础。

## 逻辑结构

```
Cluster（集群）
  └── Node（节点）
        └── Index（索引，类似表）
              └── Shard（分片）
                    └── Document（文档，JSON 行）
```

## Index（索引）

- 同类文档的集合
- 命名小写：`logs-2026.08.19`、`products`
- 通过 **mapping** 定义字段类型

## Document（文档）

```json
{
  "_index": "products",
  "_id": "1",
  "_source": {
    "title": "OpenSearch 入门书",
    "price": 59.9,
    "tags": ["search", "ops"]
  }
}
```

- 每条文档有唯一 `_id`
- 内容为 JSON `_source`

## Shard（分片）

| 类型 | 作用 |
|------|------|
| Primary Shard | 主分片，写入入口 |
| Replica Shard | 副本，读扩展 + 高可用 |

```
Index products, 3 primary + 1 replica
→ 共 6 个 shard（3 primary + 3 replica）
```

- 创建索引后 **primary 数不可改**（需 reindex）
- replica 数可动态调整

## 近实时（Near Real-Time）

```
写入 → 内存 buffer → refresh（默认 1s）→ 可搜索
                              ↓
                         flush → 磁盘 segment
```

写入后约 **1 秒** 可搜（可调 `refresh_interval`）。

## 与关系数据库对照

| OpenSearch | RDBMS |
|------------|-------|
| Index | Table |
| Document | Row |
| Field | Column |
| Mapping | Schema |
| Shard | 分区（但更灵活） |

## 集群状态

```bash
curl localhost:9200/_cat/indices?v
curl localhost:9200/_cat/shards?v
curl localhost:9200/_cluster/health?pretty
```

`green` / `yellow` / `red` 表示副本与可用性。

掌握 Index-Document-Shard 三层，后续 API 操作会顺很多。
