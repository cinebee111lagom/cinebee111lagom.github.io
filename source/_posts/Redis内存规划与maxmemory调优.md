---
title: Redis 内存规划与 maxmemory 调优
date: 2026-08-13 15:30:00
tags:
  - Redis
  - 内存
categories:
  - Redis SRE
---

Redis 是内存数据库，**OOM 即服务不可用**。内存规划是部署第一关。

## 容量估算

```
所需内存 ≈ 数据大小 × (1.2~1.5) + 缓冲区 + 复制 backlog
```

- 预留 **20~30%** 给 fork、碎片、复制缓冲
- 单实例建议 **≤ 32GB**（过大则 RDB fork 慢、重启久）

## maxmemory 配置

```conf
maxmemory 24gb
maxmemory-policy allkeys-lru
```

## 淘汰策略

| 策略 | 行为 |
|------|------|
| volatile-lru | 过期 key 中 LRU 淘汰 |
| allkeys-lru | 所有 key LRU（缓存常用） |
| volatile-ttl | 优先删 TTL 短的 |
| noeviction | 满则写报错（队列场景） |

## 内存碎片

```bash
redis-cli INFO memory
# mem_fragmentation_ratio > 1.5 需关注
```

处理：重启实例、Redis 4+ `activedefrag yes`：

```conf
activedefrag yes
active-defrag-threshold-lower 10
```

## 部署规范

- 容器/K8s 设置 **memory limit ≥ maxmemory + 20%**
- 禁止与其他内存大户同节点无隔离
- 监控 `used_memory_rss`、`evicted_keys`

内存打满前告警，而非打满后故障。
