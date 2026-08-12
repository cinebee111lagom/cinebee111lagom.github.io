---
title: Kafka 多机房容灾与 MirrorMaker 2
date: 2026-08-16 13:00:00
tags:
  - Kafka
  - 容灾
  - MirrorMaker
categories:
  - Kafka SRE
---

多机房 Kafka 容灾靠**独立集群 + MirrorMaker 2** 异步复制，而非 stretched cluster。

## 拓扑

```
Region A（Primary Cluster）
    │ MM2 异步复制
Region B（DR Cluster）
    │ 可选：Consumer 读 DR
Region C（对象存储 / Tiered Storage 归档）
```

## MirrorMaker 2 配置

```properties
clusters = primary, dr
primary.bootstrap.servers = primary-kafka:9092
dr.bootstrap.servers = dr-kafka:9092

primary->dr.enabled = true
primary->dr.topics = .*
primary->dr.groups = .*
primary->dr.sync.topic.acls.enabled = true

replication.factor = 3
checkpoints.topic.replication.factor = 3
heartbeats.topic.replication.factor = 3
offset-syncs.topic.replication.factor = 3
```

## 切换流程

### 计划切换

1. 确认 MM2 lag ≈ 0
2. 停 Primary 写入（或双写窗口结束）
3. 客户端 bootstrap 切 DR
4. Consumer offset 从 checkpoint 恢复

### 故障切换

1. Primary 不可达确认
2. 提升 DR 为写入目标
3. 应用改 bootstrap servers
4. Primary 恢复后反向 MM2 或重建

## Offset 同步

MM2 同步 Consumer Group offset 到 DR，切换后从近似位置消费。

## 延迟与 RPO

```
RPO ≈ MM2 复制延迟（通常秒~分钟级）
跨 Region 带宽 ≥ 峰值写入 × 1.2
```

## 注意事项

- Topic 配置、ACL 需同步策略
- 双向复制防循环：`replication.policy.separator`
- Schema Registry 需独立或联合（复杂）

## 检查清单

- [ ] DR 集群独立部署（非 stretched）
- [ ] MM2 lag 监控 + 告警
- [ ] 季度切换演练
- [ ] 应用 bootstrap 可配置化
- [ ] 切换 Runbook 含 offset 处理

**Kafka 多活写同一集群跨 DC 不推荐**，MM2 是主流 DR 方案。
