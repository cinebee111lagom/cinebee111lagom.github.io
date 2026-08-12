---
title: OpenSearch 性能调优入门
date: 2026-08-19 13:00:00
tags:
  - OpenSearch
  - 性能
categories:
  - OpenSearch 入门
---

OpenSearch 性能调优分**写入、搜索、集群资源**三块。

## JVM 堆内存

```yaml
OPENSEARCH_JAVA_OPTS=-Xms4g -Xmx4g
```

- 堆 ≤ **50%** 物理内存（留一半给 OS cache）
- **Xms = Xmx**，避免 resize
- 不超过 32GB（压缩指针）

## 写入优化

```json
PUT /logs/_settings
{
  "refresh_interval": "30s",
  "number_of_replicas": 0
}
```

| 手段 | 说明 |
|------|------|
| 增大 refresh_interval | 降低 segment 刷新频率 |
| 批量 Bulk | 5~15MB/批 |
| 导入时 replicas=0 | 完后再恢复 |
| 禁用不必要的 _source 压缩 | 视情况 |

## 搜索优化

| 手段 | 说明 |
|------|------|
| filter 代替 must | 不算分，可缓存 |
| `_source` 过滤 | 只取需要的字段 |
| search_after | 替代深分页 |
| 合理 shard 数 | 单 shard 20~50GB 参考 |

## Shard 数量

```
过多 shard → 元数据开销、查询 fan-out
过少 shard → 无法水平扩展

建议：primary shard 数 ≈ 数据节点数（起步）
日志按日滚索引，单索引 shard 2~5 个
```

## 磁盘与 OS

```bash
# Linux
vm.max_map_count=262144
# 不用 swap 或 swappiness=1
# SSD/NVMe
```

## 慢查询排查

```bash
# 开启慢日志
PUT /logs/_settings
{
  "index.search.slowlog.threshold.query.warn": "10s",
  "index.indexing.slowlog.threshold.index.warn": "10s"
}
```

Profile API：

```json
GET /products/_search
{
  "profile": true,
  "query": { "match": { "title": "test" } }
}
```

## 缓存

- **Query Cache**：filter 复用
- **Request Cache**：size=0 的聚合
- Field Data 已 deprecated，用 keyword/doc values

## 入门原则

1. 先定位瓶颈（写入 vs 查询 vs 磁盘）
2. mapping 合理（少 text 多 keyword）
3. 监控 heap、GC、disk、search latency

性能调优是**迭代过程**，勿一次改所有参数。
