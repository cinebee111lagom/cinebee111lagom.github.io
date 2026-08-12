---
title: OpenSearch REST API 基础
date: 2026-08-19 09:45:00
tags:
  - OpenSearch
  - REST API
categories:
  - OpenSearch 入门
---

OpenSearch 所有操作通过 **HTTP REST API** 完成，URL 结构清晰。

## URL 格式

```
<HTTP方法> /<index>/<type?>/<_action>/<id?>
```

OpenSearch 2.x 已移除 type，简化为：

```
GET /products/_search
PUT /products/_doc/1
POST /products/_doc
DELETE /products/_doc/1
```

## 常用 HTTP 方法

| 方法 | 用途 |
|------|------|
| GET | 查询、获取 |
| PUT | 创建/全量替换（需指定 id） |
| POST | 创建（自动 id）、搜索、_bulk |
| DELETE | 删除 |
| HEAD | 检查存在 |

## 集群级 API

```bash
# 健康
GET /_cluster/health

# 节点
GET /_cat/nodes?v

# 索引列表
GET /_cat/indices?v
```

## 索引级 API

```bash
# 创建索引
PUT /my-index

# 查看 mapping
GET /my-index/_mapping

# 删除索引
DELETE /my-index
```

## 文档级 API

```bash
# 写入（指定 id）
PUT /products/_doc/1
Content-Type: application/json
{"title": "book", "price": 29.9}

# 写入（自动 id）
POST /products/_doc
{"title": "book2"}

# 读取
GET /products/_doc/1

# 更新部分字段
POST /products/_update/1
{"doc": {"price": 39.9}}

# 删除
DELETE /products/_doc/1
```

## curl 示例

```bash
curl -X PUT "localhost:9200/products/_doc/1" \
  -H "Content-Type: application/json" \
  -d '{"title":"OpenSearch Guide","price":59.9}'

curl "localhost:9200/products/_doc/1?pretty"
```

## 批量操作

```bash
POST /_bulk
{ "index": { "_index": "products", "_id": "2" } }
{ "title": "item2", "price": 10 }
{ "delete": { "_index": "products", "_id": "1" } }
```

## 响应结构

```json
{
  "_index": "products",
  "_id": "1",
  "_version": 1,
  "result": "created",
  "_shards": { "total": 2, "successful": 1, "failed": 0 }
}
```

错误时 HTTP 4xx/5xx + `error.reason` 字段说明原因。

REST API 是 OpenSearch 的通用语言，Dashboards 底层同样调用这些接口。
