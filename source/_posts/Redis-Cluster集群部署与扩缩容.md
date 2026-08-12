---
title: Redis Cluster 集群部署与扩缩容
date: 2026-08-13 15:00:00
tags:
  - Redis
  - Cluster
categories:
  - Redis SRE
---

**Redis Cluster** 提供数据分片（16384 slots）与自动 failover，适合大数据量场景。

## 最小集群

- **6 节点**：3 主 3 从（每主 1 从）
- 每主负责部分 hash slot

## 创建集群

```bash
# 各节点 redis.conf
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes

# 创建（Redis 5+）
redis-cli --cluster create \
  10.0.1.11:6379 10.0.1.12:6379 10.0.1.13:6379 \
  10.0.1.21:6379 10.0.1.22:6379 10.0.1.23:6379 \
  --cluster-replicas 1 -a password
```

## 扩缩容

**扩容**（加主加从）：

```bash
redis-cli --cluster add-node new_host:6379 existing_host:6379 -a pass
redis-cli --cluster reshard existing_host:6379 --cluster-from all --cluster-to new_node_id --cluster-slots 4096
```

**缩容**：先 `reshard` 迁空 slot，再 `del-node`。

## 客户端要求

- 必须 Cluster-aware 客户端
- 支持 MOVED / ASK 重定向
- 避免跨 slot 多 key 事务（用 hash tag `{user}:id`）

## 运维监控

```bash
redis-cli --cluster check host:6379 -a pass
redis-cli CLUSTER NODES
redis-cli CLUSTER INFO
```

关注 `cluster_state:fail`、`slots_fail`。

## Cluster vs Sentinel

| | Cluster | Sentinel |
|---|---------|----------|
| 分片 | ✅ | ❌ |
| 内存上限 | 水平扩展 | 单主上限 |
| 运维 | 迁移/reshard | 相对简单 |

Cluster 是**超大规模缓存**的标准架构。
