---
title: OpenSearch 集群健康与节点角色
date: 2026-08-19 11:45:00
tags:
  - OpenSearch
  - 集群
  - 节点
categories:
  - OpenSearch 入门
---

了解集群状态与节点角色，是从小白走向运维的第一步。

## 集群健康

```bash
GET /_cluster/health?pretty
```

| 状态 | 含义 |
|------|------|
| green | 所有 primary + replica 正常 |
| yellow | primary 正常，部分 replica 未分配 |
| red | 部分 primary 未分配，数据可能不可用 |

单节点集群 replica 无法分配 → 常显示 **yellow**（学习环境正常）。

## 节点角色

| 角色 | 作用 |
|------|------|
| cluster_manager（原 master） | 集群元数据、索引创建 |
| data | 存数据、执行 CRUD/搜索 |
| ingest | 预处理 pipeline |
| coordinating | 仅路由请求（可选） |

小集群节点可身兼多职；大集群建议专用 cluster_manager 节点（3 个）。

## 查看节点

```bash
GET /_cat/nodes?v&h=name,node.role,heap.percent,disk.used_percent

GET /_nodes/stats
```

## 分片分配

```bash
GET /_cat/shards?v
GET /_cluster/allocation/explain
{
  "index": "logs-2026.08.19",
  "shard": 0,
  "primary": true
}
```

解释 shard 为何未分配（磁盘满、节点下线等）。

## 常用 settings

```bash
# 单节点关闭 replica
PUT /my-index/_settings
{ "number_of_replicas": 0 }

# 集群级副本
PUT /_cluster/settings
{
  "persistent": {
    "cluster.routing.allocation.enable": "all"
  }
}
```

## 脑裂与 quorum

- cluster_manager 节点数建议 **3**（奇数）
- `discovery.seed_hosts` 配置初始发现

## 入门建议

| 环境 | 配置 |
|------|------|
| 本地 Docker | single-node，yellow 可接受 |
| 生产最小 | 3 data + 3 cluster_manager 分离 |
| 磁盘 | 使用率 < 85% |

`/_cluster/health` 和 `/_cat/shards` 是排查问题的第一反应。
