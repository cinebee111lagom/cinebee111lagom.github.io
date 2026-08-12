---
title: OpenSearch 索引模板与别名
date: 2026-08-19 11:30:00
tags:
  - OpenSearch
  - 索引模板
  - 别名
categories:
  - OpenSearch 入门
---

日志场景每天建新索引，**索引模板**和**别名**让管理自动化、查询统一化。

## Index Template（索引模板）

匹配新索引名，自动应用 settings + mapping：

```bash
PUT /_index_template/logs-template
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "5s"
    },
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "message": { "type": "text" },
        "level": { "type": "keyword" },
        "host": { "type": "keyword" }
      }
    }
  },
  "priority": 100
}
```

创建 `logs-2026.08.19` 时自动套用。

## Composable Template

OpenSearch 2.x 推荐 composable index template（如上 `_index_template` API），替代旧 `_template`。

## Alias（别名）

```bash
# 创建别名指向多个索引
POST /_aliases
{
  "actions": [
    { "add": { "index": "logs-2026.08.18", "alias": "logs-read" } },
    { "add": { "index": "logs-2026.08.19", "alias": "logs-read" } }
  ]
}

# 查询别名 = 查所有关联索引
GET /logs-read/_search
```

## 写入别名（日志滚动）

```bash
POST /_aliases
{
  "actions": [
    { "add": { "index": "logs-2026.08.19", "alias": "logs-write", "is_write_index": true } },
    { "remove": { "index": "logs-2026.08.18", "alias": "logs-write" } }
  ]
}
```

应用始终写 `logs-write`，后台按日滚索引。

## ISM（索引生命周期）

```bash
PUT /_plugins/_ism/policies/logs-policy
{
  "policy": {
    "description": "logs lifecycle",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [],
        "transitions": [{ "state_name": "delete", "conditions": { "min_index_age": "30d" } }]
      },
      { "name": "delete", "actions": [{ "delete": {} }] }
    ]
  }
}
```

30 天后自动删索引。

## 最佳实践

- 日志：`logs-<app>-YYYY.MM.DD` + 模板
- 搜索业务：单索引 + alias 零停机 reindex 切换
- 模板 versioning：改 mapping 用新 template name + 新 index pattern

模板和别名是**运维日志索引**的必备技能。
