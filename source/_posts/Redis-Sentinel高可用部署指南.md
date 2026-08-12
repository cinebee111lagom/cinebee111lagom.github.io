---
title: Redis Sentinel 高可用部署指南
date: 2026-08-13 14:45:00
tags:
  - Redis
  - Sentinel
categories:
  - Redis SRE
---

**Sentinel** 监控主从健康，主库故障时自动选举新主，实现 Redis HA。

## 架构要求

- 至少 **3 个 Sentinel** 节点（奇数，避免脑裂误判）
- 1 主 + N 从（建议 ≥ 2 从，留 failover 候选）
- Sentinel 独立部署，不与 Redis 争资源

## Sentinel 配置（sentinel.conf）

```conf
port 26379
sentinel monitor mymaster 10.0.1.10 6379 2
sentinel auth-pass mymaster your_master_password
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
```

| 参数 | 含义 |
|------|------|
| `quorum 2` | 至少 2 个 Sentinel 认为主观下线 |
| `down-after-milliseconds 5000` | 5s 无响应判主观下线 |
| `parallel-syncs 1` | 同时向新主同步的从库数 |

## 客户端配置

使用 Sentinel 模式连接，非直连 IP：

```
redis-sentinel://sentinel1:26379,sentinel2:26379,sentinel3:26379/mymaster
```

Jedis、Lettuce、redis-py 均支持 `Sentinel` 客户端。

## Failover 流程

1. SDOWN（主观下线）→ ODOWN（客观下线，quorum 达成）
2. Sentinel 选举 Leader 执行 failover
3. 从库按 priority、offset 选新主
4. 其余从库 `REPLICAOF` 新主
5. 旧主恢复后变从库

## 运维注意

- **不要** 3 个 Sentinel 放同一物理机
- 监控 `sentinel_masters` 与 failover 事件
- 定期演练： `redis-cli -p 26379 SENTINEL failover mymaster`

Sentinel 适合 **单分片、内存 < 64GB** 的核心缓存场景。
