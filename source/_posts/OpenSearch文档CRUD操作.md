---
title: OpenSearch 文档 CRUD 操作
date: 2026-08-19 10:15:00
tags:
  - OpenSearch
  - CRUD
categories:
  - OpenSearch 入门
---

文档的增删改查是日常最常用的操作。

## Create（创建）

```bash
# 指定 ID（存在则全量覆盖，version+1）
PUT /products/_doc/1
{
  "title": "OpenSearch 实战",
  "price": 68.0,
  "sku": "BK-001"
}

# 自动生成 ID
POST /products/_doc
{
  "title": "新书上架"
}
```

## Read（读取）

```bash
# 按 ID
GET /products/_doc/1

# 只取部分字段
GET /products/_doc/1?_source_includes=title,price

# 不存在返回 404
GET /products/_doc/999
```

## Update（更新）

```bash
# 部分更新（推荐）
POST /products/_update/1
{
  "doc": {
    "price": 58.0
  }
}

# 脚本更新
POST /products/_update/1
{
  "script": {
    "source": "ctx._source.stock -= params.qty",
    "params": { "qty": 1 }
  }
}
```

## Delete（删除）

```bash
DELETE /products/_doc/1

# 按查询删除
POST /products/_delete_by_query
{
  "query": {
    "term": { "sku": "BK-001" }
  }
}
```

## 乐观锁（版本控制）

```bash
PUT /products/_doc/1?if_seq_no=0&if_primary_term=1
{ "title": "updated" }
# 版本冲突返回 409
```

## Bulk 批量写入

```bash
POST /_bulk
{ "index": { "_index": "products", "_id": "10" } }
{ "title": "bulk-1", "price": 10 }
{ "index": { "_index": "products", "_id": "11" } }
{ "title": "bulk-2", "price": 20 }
```

```bash
# 从文件导入
curl -H "Content-Type: application/x-ndjson" \
  -X POST localhost:9200/_bulk \
  --data-binary @bulk.ndjson
```

## 响应字段

| 字段 | 含义 |
|------|------|
| `result` | created / updated / deleted / noop |
| `_version` | 文档版本号 |
| `_shards.successful` | 成功写入的分片数 |

## 注意

- PUT 全量替换未传字段会**丢失**
- 更新走 `_update`，内部 merge 后 reindex 文档
- Bulk 建议每批 5~15MB，失败项在 `items` 数组中单独返回

CRUD 熟练后，可以进入搜索与聚合。
