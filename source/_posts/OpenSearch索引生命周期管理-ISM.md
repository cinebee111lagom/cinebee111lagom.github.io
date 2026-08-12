---
title: OpenSearch 索引生命周期管理（ISM）
date: 2026-08-20 11:00:00
tags:
  - OpenSearch
  - ISM
  - 生命周期
categories:
  - OpenSearch SRE
---

ISM（Index State Management）自动管理索引从热到删的全生命周期，日志平台必备。

## ISM 策略示例

```bash
PUT /_plugins/_ism/policies/logs-retention
{
  "policy": {
    "description": "Logs hot 7d → warm 23d → delete 30d",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [],
        "transitions": [{
          "state_name": "warm",
          "conditions": { "min_index_age": "7d" }
        }]
      },
      {
        "name": "warm",
        "actions": [
          { "replica_count": { "number_of_replicas": 0 } },
          { "shrink": { "num_new_shards": 1 } }
        ],
        "transitions": [{
          "state_name": "delete",
          "conditions": { "min_index_age": "30d" }
        }]
      },
      {
        "name": "delete",
        "actions": [{ "delete": {} }]
      }
    ],
    "ism_template": [{
      "index_patterns": ["logs-*"],
      "priority": 100
    }]
  }
}
```

## 应用到索引

```bash
POST /_plugins/_ism/add/logs-2026.08.20
{ "policy_id": "logs-retention" }
```

新索引匹配 `ism_template` 自动关联。

## 常用 Action

| Action | 作用 |
|--------|------|
| rollover | 索引大小/文档数/时间滚动 |
| shrink | 减少 shard |
| force_merge | 合并 segment（只读索引） |
| allocate | 迁移到 warm 节点 |
| delete | 删除索引 |
| snapshot | 转快照后删 |

## Rollover 别名模式

```bash
PUT /_index_template/logs-rollover
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "opensearch.index_state_management.rollover_alias": "logs-write"
    }
  }
}
```

## 监控 ISM

```bash
GET /_plugins/_ism/explain/logs-2026.08.20?pretty
```

失败 action 需告警。

## 最佳实践

- 日志保留天数合规化写入 ISM
- delete 前确保 snapshot 已覆盖
- warm 节点用 `node.attr.temp: warm` + allocate
- 大索引 shrink 在低峰执行

ISM 是 **磁盘成本与合规 retention** 的核心杠杆。
