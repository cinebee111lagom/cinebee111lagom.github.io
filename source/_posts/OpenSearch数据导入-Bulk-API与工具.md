---
title: OpenSearch 数据导入：Bulk API 与工具
date: 2026-08-19 12:00:00
tags:
  - OpenSearch
  - Bulk
  - 导入
categories:
  - OpenSearch 入门
---

大批量写入必须用 **Bulk API** 或专用工具，单条 PUT 效率太低。

## Bulk 格式（NDJSON）

```json
{ "index": { "_index": "products", "_id": "1" } }
{ "title": "book1", "price": 10 }
{ "index": { "_index": "products", "_id": "2" } }
{ "title": "book2", "price": 20 }
{ "create": { "_index": "products", "_id": "3" } }
{ "title": "book3", "price": 30 }
{ "update": { "_index": "products", "_id": "1" } }
{ "doc": { "price": 12 } }
{ "delete": { "_index": "products", "_id": "2" } }
```

每两行一组：action 行 + 可选 source 行。

## curl 导入

```bash
curl -H "Content-Type: application/x-ndjson" \
  -X POST localhost:9200/_bulk \
  --data-binary @data.ndjson
```

## 响应与错误处理

```json
{
  "errors": true,
  "items": [
    { "index": { "status": 201, ... } },
    { "index": { "status": 400, "error": { "reason": "..." } } }
  ]
}
```

`errors: true` 时需逐条检查 `items`，失败项可重试。

## 批量大小建议

| 参数 | 建议 |
|------|------|
| 每批文档数 | 500~5000 |
| 每批大小 | 5~15 MB |
| 并发线程 | 与 shard 数相当 |

过大 → 内存压力；过小 → 吞吐低。

## OpenSearch Dashboards Dev Tools

```
POST /_bulk
{ "index": { "_index": "test" } }
{ "field": "value" }
```

## 外部工具

| 工具 | 场景 |
|------|------|
| **Logstash** | 持续采集转换写入 |
| **Filebeat** | 轻量日志采集 |
| **opensearch-dump** | 索引间迁移 |
| **curl + jq** | 脚本化小批量 |

```bash
# opensearch-dump 示例
elasticdump --input=http://src:9200/my-index \
            --output=http://dst:9200/my-index \
            --type=data
```

## 导入前准备

- [ ] 索引 mapping 已创建
- [ ] 临时调大 `refresh_interval`（如 30s）提升写入
- [ ] 导入完恢复 `refresh_interval`
- [ ] 大批量关闭 replica，完后再开

Bulk 是 OpenSearch **写入性能**的核心接口。
