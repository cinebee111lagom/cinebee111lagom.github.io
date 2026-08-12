---
title: OpenSearch 性能调优 SRE 实践
date: 2026-08-20 11:15:00
tags:
  - OpenSearch
  - 性能调优
categories:
  - OpenSearch SRE
---

生产性能调优分 **写入、搜索、资源** 三线，需 metrics 驱动。

## 写入优化

```bash
PUT /logs-write/_settings
{
  "refresh_interval": "30s",
  "number_of_replicas": 0,
  "translog.durability": "async"
}
```

| 手段 | 效果 |
|------|------|
| Bulk 5~15MB | 提高吞吐 |
| 导入时 replicas=0 | 减半写入 |
| 增大 refresh_interval | 减 segment 刷新 |
| ingest pipeline 简化 | 降 CPU |

导入完成后恢复 replicas 与 refresh。

## 搜索优化

| 手段 | 说明 |
|------|------|
| filter 上下文 | 不算分，可 cache |
| `_source` filtering | 减网络 |
| search_after | 替代 from+size 深分页 |
| 合理 shard 数 | 减 fan-out |

## 分片与 rebalance

```bash
GET /_cat/shards?v&s=store.size:desc
GET /_cluster/stats/indices?filter_path=indices.shards
```

过多小 shard → 合并（shrink）或 reindex。

## JVM/GC

- G1GC 默认
- 监控 `jvm_gc_collection_seconds`
- Full GC 频繁 → 减 fielddata、优化 agg

## Circuit Breaker

```bash
GET /_nodes/stats/breaker
```

parent/request/fielddata breaker  trip → 查询/agg 过大。

## 调优流程

1. 基线：indexing rate、search P99、disk
2. 定位瓶颈（hot_threads、thread_pool rejected）
3. 单变量变更
4. 压测验证

## SRE Checklist

- [ ] 无 rejected write/search
- [ ] 单 shard < 50GB
- [ ] 慢查询 Top N 定期 review
- [ ] 无 fielddata 滥用（text 聚合）

性能问题 **先查 thread_pool 和 disk，再加机器**。
