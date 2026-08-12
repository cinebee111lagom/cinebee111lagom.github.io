---
title: OpenSearch 聚合（Aggregation）入门
date: 2026-08-19 10:45:00
tags:
  - OpenSearch
  - 聚合
  - Aggregation
categories:
  - OpenSearch 入门
---

聚合用于**统计分析**，类似 SQL 的 `GROUP BY` + 聚合函数。

## 聚合类型概览

| 类型 | 作用 | 示例 |
|------|------|------|
| Metric | 算数值 | avg、sum、max |
| Bucket | 分组 | terms、date_histogram |
| Pipeline | 基于其他聚合结果 | derivative |

## 指标聚合

```bash
GET /products/_search
{
  "size": 0,
  "aggs": {
    "avg_price": { "avg": { "field": "price" } },
    "max_price": { "max": { "field": "price" } },
    "total_stock": { "sum": { "field": "stock" } }
  }
}
```

`size: 0` 不返回文档，只要聚合结果。

## terms 分组（Top N）

```bash
GET /products/_search
{
  "size": 0,
  "aggs": {
    "by_tag": {
      "terms": {
        "field": "tags",
        "size": 10
      }
    }
  }
}
```

## 嵌套聚合

```bash
GET /products/_search
{
  "size": 0,
  "aggs": {
    "by_tag": {
      "terms": { "field": "tags" },
      "aggs": {
        "avg_price": { "avg": { "field": "price" } }
      }
    }
  }
}
```

每个 tag  bucket 内的平均价格。

## 日期直方图

```bash
GET /logs/_search
{
  "size": 0,
  "aggs": {
    "logs_over_time": {
      "date_histogram": {
        "field": "@timestamp",
        "calendar_interval": "1h"
      }
    }
  }
}
```

Dashboards 时序图的基础。

## 过滤 + 聚合

```json
{
  "query": {
    "range": { "@timestamp": { "gte": "now-24h" } }
  },
  "aggs": {
    "status_codes": {
      "terms": { "field": "status" }
    }
  }
}
```

## 注意

- 聚合字段需 `keyword` 或数值类型（text 需 `.keyword`）
- `terms.size` 默认 10，Top N 需调大
- 高基数 field（如 user_id）terms 聚合可能慢

聚合 + 搜索组合，可实现「筛选后统计」的日志分析场景。
