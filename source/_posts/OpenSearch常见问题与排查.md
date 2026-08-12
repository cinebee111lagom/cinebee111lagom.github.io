---
title: OpenSearch 常见问题与排查
date: 2026-08-19 13:30:00
tags:
  - OpenSearch
  - 排查
  - 常见问题
categories:
  - OpenSearch 入门
---

OpenSearch 新手常见问题汇总与排查思路。

## 集群 red

```bash
GET /_cluster/health
GET /_cat/shards?v | grep UNASSIGNED
GET /_cluster/allocation/explain
```

| 原因 | 解决 |
|------|------|
| 磁盘 > 95% | 删旧索引、扩容 |
| 节点 down | 恢复节点 |
| shard 损坏 | restore snapshot |

## 搜不到数据

| 原因 | 检查 |
|------|------|
| refresh 延迟 | 等 1s 或 `POST /index/_refresh` |
| 查错索引/别名 | `/_cat/indices` |
| text 用 term 搜 | 改用 match |
| mapping 不对 | `/_mapping` |
| 分词不匹配 | `/_analyze` 测试 |

## 写入 rejected

```
429 Too Many Requests / circuit_breaking_exception
```

- JVM heap 过高 → 扩内存、清 fielddata cache
- 磁盘 watermark → 清理磁盘
- 批量过大 → 减小 bulk size

## yellow 单节点

```
unassigned replica
```

学习：`number_of_replicas: 0`  
生产：加节点或接受 yellow 风险（无副本）

## mapping 冲突

```
mapper parsing exception: failed to parse field
```

- 动态 mapping 推断类型与后续文档冲突
- 解决：新索引 + 正确 mapping + reindex

## 内存 OOM

```bash
grep -i OutOfMemoryError /var/log/opensearch/*.log
```

- 堆太小 → 调 `-Xmx`
- 堆太大 → 不超过 32GB
- 聚合 cardinality 过高 → 优化查询

## 连接 Dashboards 失败

- `OPENSEARCH_HOSTS` 地址错误
- HTTPS/HTTP 混用
- 认证密码错误

## 排查工具箱

```bash
GET /_cat/health?v
GET /_cat/nodes?v
GET /_cat/indices?v&s=store.size:desc
GET /_nodes/hot_threads
GET /_cluster/stats
```

## 日志位置

```
Docker: docker logs <container>
Linux: /var/log/opensearch/
```

**万能法则**：health → shards → logs，逐层缩小范围。
