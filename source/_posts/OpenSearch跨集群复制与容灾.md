---
title: OpenSearch 跨集群复制与容灾
date: 2026-08-20 12:45:00
tags:
  - OpenSearch
  - 容灾
  - CCR
categories:
  - OpenSearch SRE
---

OpenSearch **Cross-Cluster Replication（CCR）** 实现索引级准实时容灾。

## CCR 架构

```
Leader Cluster (Region A)          Follower Cluster (Region B)
  Index: logs-2026.08.20    →→→      Index: logs-2026.08.20 (read-only replica)
```

## 配置远程集群

```bash
# Follower 上配置 Leader 连接
PUT /_cluster/settings
{
  "persistent": {
    "cluster.remote.leader-cluster.seeds": ["leader-os:9300"]
  }
}
```

需双向 transport TLS 信任。

## 启动复制

```bash
PUT /_plugins/_replication/logs-2026.08.20/_start
{
  "leader_alias": "leader-cluster",
  "leader_index": "logs-2026.08.20",
  "use_roles": {
    "leader_cluster_role": "all_access",
    "follower_cluster_role": "all_access"
  }
}
```

## 故障切换

```
1. 停止 Leader 写入
2. 确认 replication lag ≈ 0
3. POST /_plugins/_replication/logs-2026.08.20/_stop
4. 提升 Follower 为独立索引（可写）
5. 应用/Dashboards 切 Follower 集群
```

## CCR vs Snapshot

| | CCR | Snapshot |
|---|-----|----------|
| RPO | 秒~分钟 | 小时~天 |
| 成本 | 双集群 | 存储便宜 |
| 复杂度 | 高 | 低 |

## 多集群搜索（CCS）

```bash
GET /leader-cluster:logs-*/_search
{
  "query": { "match_all": {} }
}
```

跨集群只读联合查询，非容灾。

## 检查清单

- [ ] Leader/Follower 网络互通 9300
- [ ] replication lag 监控告警
- [ ] 季度 failover 演练
- [ ] 与 Snapshot 互补（CCR + 日快照）

容灾方案需在 **RPO/RTO** 文档中明确 CCR 或 Snapshot 主路径。
