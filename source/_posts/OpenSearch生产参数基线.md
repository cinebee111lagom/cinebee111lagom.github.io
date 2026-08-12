---
title: OpenSearch 生产参数基线
date: 2026-08-20 10:00:00
tags:
  - OpenSearch
  - 参数
categories:
  - OpenSearch SRE
---

OpenSearch 生产参数覆盖 JVM、索引默认值、集群路由与线程池。

## JVM（16GB 堆示例）

```
-Xms16g
-Xmx16g
-XX:+UseG1GC
-XX:G1ReservePercent=25
-XX:InitiatingHeapOccupancyPercent=30
```

## opensearch.yml 集群级

```yaml
cluster.routing.allocation.disk.watermark.low: 85%
cluster.routing.allocation.disk.watermark.high: 90%
cluster.routing.allocation.disk.watermark.flood_stage: 95%

action.destructive_requires_name: true
cluster.max_shards_per_node: 1000
```

## 索引默认 template

```bash
PUT /_index_template/default-prod
{
  "index_patterns": ["*"],
  "priority": 1,
  "template": {
    "settings": {
      "number_of_replicas": 1,
      "refresh_interval": "5s",
      "translog.durability": "async",
      "translog.sync_interval": "5s",
      "index.codec": "best_compression"
    }
  }
}
```

日志高写入可 `refresh_interval: 30s`。

## 线程池（通常默认即可）

| 池 | 用途 | 拒绝时 |
|----|------|--------|
| write | 索引写入 | 429 |
| search | 查询 | 429 |
| management | 集群管理 | — |

```bash
GET /_nodes/thread_pool?filter_path=*.write,*.search
```

## 慢日志

```bash
PUT /logs-*/_settings
{
  "index.search.slowlog.threshold.query.warn": "5s",
  "index.indexing.slowlog.threshold.index.warn": "5s"
}
```

## 生产 vs 开发

| 参数 | 开发 | 生产 |
|------|------|------|
| replicas | 0 | ≥1 |
| Security | 可关 | 必须开 |
| auto_create_index | true | false |
| snapshot | 无 | 每日 |

## 调优原则

- 堆不超过 32GB
- 磁盘使用率 < 85%
- 变更走 `_cluster/settings` persistent，文档化

参数变更后观察 GC、search latency、bulk rejections。
