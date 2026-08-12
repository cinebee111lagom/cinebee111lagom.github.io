---
title: OpenSearch 冷热分层与存储优化
date: 2026-08-20 13:30:00
tags:
  - OpenSearch
  - 冷热分层
  - 存储
categories:
  - OpenSearch SRE
---

冷热分层通过 **不同硬件节点 + ISM allocate** 降低长期存储成本。

## 节点属性

```yaml
# 热节点
node.attr.temp: hot
node.roles: [data, ingest]

# 温/冷节点
node.attr.temp: warm
node.roles: [data]
# 挂大容量 HDD
```

## ISM allocate

```json
{
  "name": "warm",
  "actions": [{
    "allocation": {
      "require": { "temp": "warm" },
      "number_of_replicas": 0
    }
  }]
}
```

7 天后索引迁移到 warm 节点，副本降为 0。

## Searchable Snapshot（冷层）

```bash
PUT /_snapshot/s3_repo
# 注册可搜索快照仓库

# ISM 将索引 mount 为 searchable snapshot
{
  "cold": {
    "actions": [{
      "searchable_snapshot": {
        "snapshot_repository": "s3_repo"
      }
    }]
  }
}
```

数据在 S3，本地缓存少量，成本最低，查询较慢。

## force_merge（温层）

```json
{
  "actions": [{
    "force_merge": { "max_num_segments": 1 }
  }]
}
```

只读索引合并 segment，减存储、提查询。

## 成本对比（示意）

| 层 | 介质 | 相对成本 | 查询性能 |
|----|------|----------|----------|
| hot | NVMe | 高 | 最好 |
| warm | HDD | 中 | 中 |
| cold | S3 searchable | 低 | 较慢 |

## 注意

- warm 节点无 replica 时节点故障需能从 snapshot 恢复
- searchable snapshot 不适合高频查询
- shrink 后再 migrate 减 shard 开销

## Checklist

- [ ] 节点 temp 属性已打标
- [ ] ISM 热→温→冷→删 全链路
- [ ] 冷层查询 SLA 与业务对齐
- [ ] 成本月度 report

冷热分层是 **日志平台降本** 的核心手段。
