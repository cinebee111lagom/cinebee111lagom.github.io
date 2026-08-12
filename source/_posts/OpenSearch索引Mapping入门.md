---
title: OpenSearch 索引 Mapping 入门
date: 2026-08-19 10:00:00
tags:
  - OpenSearch
  - Mapping
categories:
  - OpenSearch 入门
---

Mapping 定义字段**名称、类型、分词方式**，相当于表结构，影响搜索与聚合行为。

## 创建带 Mapping 的索引

```bash
PUT /products
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "standard"
      },
      "sku": {
        "type": "keyword"
      },
      "price": {
        "type": "double"
      },
      "stock": {
        "type": "integer"
      },
      "created_at": {
        "type": "date"
      },
      "tags": {
        "type": "keyword"
      }
    }
  }
}
```

## 常用字段类型

| 类型 | 用途 | 可全文搜索 | 可聚合 |
|------|------|------------|--------|
| `text` | 全文检索 | ✅（分词） | ❌ |
| `keyword` | 精确匹配、排序、聚合 | ❌ | ✅ |
| `long`/`integer`/`double` | 数值 | ❌ | ✅ |
| `date` | 时间 | ❌ | ✅ |
| `boolean` | 布尔 | ❌ | ✅ |
| `object` | 嵌套 JSON | — | — |
| `nested` | 数组对象独立查询 | — | — |

## text vs keyword

```json
"title": {
  "type": "text",
  "fields": {
    "keyword": {
      "type": "keyword",
      "ignore_above": 256
    }
  }
}
```

- `title` → 全文搜「OpenSearch 入门」
- `title.keyword` → 精确匹配、排序

## 动态 Mapping

未定义字段首次写入时自动推断类型：

```json
{"count": "123"}   // 可能推断为 text + keyword 双字段
{"count": 123}     // long
```

生产环境建议 **显式 mapping**，避免类型冲突。

## 查看与修改

```bash
GET /products/_mapping

# 新增字段（不可改已有字段类型）
PUT /products/_mapping
{
  "properties": {
    "brand": { "type": "keyword" }
  }
}
```

改类型需 **reindex** 到新索引。

## 最佳实践

- 能 `keyword` 就不 `text`（ID、状态码、枚举）
- 日期统一 `date` 格式
- 禁用 `_source` 仅当明确不需要原文（少见）

Mapping 设计错了后期代价大，**先设计再灌数据**。
