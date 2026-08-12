---
title: OpenSearch 慢查询与集群诊断
date: 2026-08-20 12:30:00
tags:
  - OpenSearch
  - 慢查询
  - 诊断
categories:
  - OpenSearch SRE
---

慢查询与集群卡顿是 OpenSearch SRE 最高频工单类型。

## 慢日志

```bash
PUT /logs-*/_settings
{
  "index.search.slowlog.threshold.query.warn": "2s",
  "index.search.slowlog.threshold.fetch.warn": "1s",
  "index.indexing.slowlog.threshold.index.warn": "2s"
}
```

日志路径：`logs/prod-opensearch_index_search_slowlog.log`

## Hot Threads

```bash
GET /_nodes/hot_threads?threads=5&type=cpu&interval=500ms
```

定位 CPU 热点（aggregation、script、merge）。

## Profile API

```json
GET /products/_search
{
  "profile": true,
  "query": {
    "bool": {
      "must": [{ "match": { "title": "test" } }],
      "filter": [{ "range": { "price": { "gte": 10 } } }]
    }
  }
}
```

分析各 phase 耗时。

## 常见慢因

| 原因 | 解决 |
|------|------|
| text 字段聚合 | 改 keyword |
| 深分页 from+size | search_after |
| wildcard 前缀 `*foo` | ngram 或 ES|QL |
| 过多 shard | shrink/coalesce |
| 大量 nested | 扁平化设计 |
| force merge 进行中 | 低峰执行 |

## Pending Tasks

```bash
GET /_cluster/pending_tasks
GET /_cat/tasks?v
```

大量 shard 分配/ relocation 阻塞集群。

## Segment 与 Merge

```bash
GET /logs-2026.08.20/_segments
GET /_nodes/stats/indices/merge
```

merge 过多 → 减 refresh、导入后 forcemerge（只读索引）。

## 诊断流程

```
1. 用户报慢 → 复现 DSL
2. slowlog + profile
3. hot_threads
4. 检查 shard 分布、disk、JVM
5. 优化 DSL 或扩容
```

## 工具

- OpenSearch Dashboards **Query Insights**（2.x）
- `_nodes/stats` 对比

慢查询治理需 **开发 + SRE** 联合 review Top N。
