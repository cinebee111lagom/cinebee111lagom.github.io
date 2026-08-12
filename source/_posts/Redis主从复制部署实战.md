---
title: Redis 主从复制部署实战
date: 2026-08-13 14:30:00
tags:
  - Redis
  - 主从
categories:
  - Redis SRE
---

主从复制是 Redis HA 的基石：一主多从，读写分离，故障时可提升从库。

## 拓扑

```
        ┌─────────┐
        │ Master  │ ← 写
        └────┬────┘
     ┌───────┼───────┐
     ▼       ▼       ▼
  Replica1 Replica2 Replica3  ← 读
```

## 主库配置（redis.conf）

```conf
bind 0.0.0.0
port 6379
requirepass your_master_password
masterauth your_master_password

# 持久化（生产建议开启 AOF）
appendonly yes
appendfsync everysec

maxmemory 8gb
maxmemory-policy allkeys-lru
```

## 从库配置

```conf
replicaof 10.0.1.10 6379
requirepass your_replica_password
masterauth your_master_password
replica-read-only yes
```

或使用命令动态添加：

```bash
redis-cli -a pass REPLICAOF 10.0.1.10 6379
```

## 验证复制

```bash
redis-cli INFO replication
# role:master / role:slave
# connected_slaves:2
# master_link_status:up
```

## 部署检查清单

- [ ] 主从 `requirepass` / `masterauth` 一致
- [ ] 防火墙仅开放 6379 给应用与从库
- [ ] 从库 `replica-read-only yes` 防止误写
- [ ] 监控 `master_link_down_since_seconds`
- [ ] 主从延迟 `master_repl_offset` 差值

## 复制延迟排查

- 网络带宽不足
- 主库写入 burst 过大
- 从库单线程回放积压

主从本身**不自动 failover**，生产需配合 Sentinel 或手动切换。
