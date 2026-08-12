---
title: OpenSearch 搜索基础：match 与 term
date: 2026-08-19 10:30:00
tags:
  - OpenSearch
  - 搜索
  - Query DSL
categories:
  - OpenSearch 入门
---

OpenSearch 使用 **Query DSL**（JSON 查询语言），`match` 与 `term` 是最基础的两个查询。

## 搜索入口

```bash
GET /products/_search
{
  "query": { ... }
}
```

## match（全文搜索）

对 `text` 字段分词后匹配：

```bash
GET /products/_search
{
  "query": {
    "match": {
      "title": "OpenSearch 入门"
    }
  }
}
```

会匹配 title 含「OpenSearch」或「入门」的文档（默认 OR）。

```json
"match": {
  "title": {
    "query": "OpenSearch 入门",
    "operator": "and"
  }
}
```

## term（精确匹配）

用于 `keyword`、数值、日期：

```bash
GET /products/_search
{
  "query": {
    "term": {
      "sku": "BK-001"
    }
  }
}
```

**不要**对 text 字段用 term 搜整句（未分词，通常搜不到）。

## terms（多值 OR）

```json
"terms": {
  "tags": ["search", "ops"]
}
```

## bool 组合查询

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "title": "OpenSearch" } }
      ],
      "filter": [
        { "range": { "price": { "gte": 10, "lte": 100 } } }
      ],
      "must_not": [
        { "term": { "status": "offline" } }
      ],
      "should": [
        { "term": { "tags": "hot" } }
      ],
      "minimum_should_match": 1
    }
  }
}
```

| 子句 | 作用 | 算分 |
|------|------|------|
| must | 必须满足 | ✅ |
| filter | 必须满足 | ❌（可缓存） |
| should | 可选加分 | ✅ |
| must_not | 必须不满足 | ❌ |

## 分页

```json
{
  "from": 0,
  "size": 10,
  "query": { "match_all": {} }
}
```

深分页（from 很大）性能差，生产用 **search_after**。

## 高亮

```json
"highlight": {
  "fields": {
    "title": {}
  }
}
```

## 选择指南

| 场景 | 查询 |
|------|------|
| 搜标题、描述 | match |
| 搜订单号、状态 | term |
| 价格区间 | range in filter |
| 多条件组合 | bool |

下一篇讲聚合（Aggregation）统计分析。
