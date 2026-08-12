---
title: Kafka 备份与灾难恢复
date: 2026-08-16 10:15:00
tags:
  - Kafka
  - 备份
  - 灾备
categories:
  - Kafka SRE
---

Kafka 是持久化日志，备份策略与数据库不同，核心是**多副本 + 跨集群复制 + Retention**。

## 备份层次

| 层次 | 方式 | RPO |
|------|------|-----|
| 副本 | replication.factor=3 | 0（ISR 内） |
| 跨集群 | MirrorMaker 2 | 秒~分钟 |
| 冷备份 | 日志目录快照 / Tiered Storage | 小时~天 |
| 应用层 | 消费落库、事件溯源 | 取决于下游 |

## MirrorMaker 2（推荐跨集群 DR）

```properties
# mm2.properties
clusters = primary, dr
primary.bootstrap.servers = 10.0.1.11:9092
dr.bootstrap.servers = 10.0.2.11:9092
primary->dr.enabled = true
primary->dr.topics = orders.*, payments.*
replication.policy.class = org.apache.kafka.connect.mirror.DefaultReplicationPolicy
```

## Tiered Storage（Kafka 3.6+ / Confluent）

```properties
remote.log.storage.system.enable=true
remote.log.manager.task.interval.ms=30000
```

冷数据 offload 到 S3，降低本地磁盘压力，**非实时 DR**。

## 日志目录快照

```bash
# Broker 停止后（或配合存储快照）
tar czf kafka-logs-$(date +%Y%m%d).tar.gz /data/kafka-logs
```

仅适合小集群或补充手段，生产依赖副本 + MM2。

## 恢复场景

| 场景 | 方案 |
|------|------|
| 单 Broker 宕机 | 自动 Leader 切换，替换 Broker |
| 整集群不可用 | 切换到 DR 集群（MM2） |
| 误删 Topic | 从 MM2 目标集群导出 / 备份恢复 |
| 数据 corruption | 从 ISR Follower 重建 |

## 检查清单

- [ ] replication.factor=3，min.insync.replicas=2
- [ ] MM2 监控 lag 与同步状态
- [ ] DR 集群定期消费验证
- [ ] Retention 满足合规（不可只依赖 7 天默认）
- [ ] 季度 DR 切换演练

**Kafka 的备份 = 副本一致性 + 跨集群复制 + 下游持久化**。
