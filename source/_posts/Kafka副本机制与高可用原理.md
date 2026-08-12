---
title: Kafka 副本机制与高可用原理
date: 2026-08-16 09:45:00
tags:
  - Kafka
  - 高可用
  - 副本
categories:
  - Kafka SRE
---

Kafka 高可用依赖分区副本、ISR 机制与 Controller 故障转移。

## 副本模型

```
Partition 0:  Leader(Broker1) ← Producer 写
              Follower(Broker2) ← 同步复制
              Follower(Broker3) ← 同步复制
```

- **Leader**：处理读写
- **Follower**：从 Leader 拉取日志
- **ISR**（In-Sync Replicas）：与 Leader 差距在阈值内的副本

## 关键参数

```properties
replication.factor=3
min.insync.replicas=2
unclean.leader.election.enable=false
replica.lag.time.max.ms=30000
```

## 生产者 acks

| acks | 语义 | 场景 |
|------|------|------|
| 0 | 不等确认 | 日志采集，可丢 |
| 1 | Leader 写入即确认 | 一般业务 |
| all/-1 | ISR 全部确认 | 金融、订单 |

配合 `min.insync.replicas=2` + `acks=all` 防单副本丢失。

## Leader 选举

Broker 宕机 → Controller 从 ISR 选新 Leader → 客户端 metadata 刷新。

**Under-Replicated Partitions (URP)**：副本未完全同步，需告警。

```bash
kafka-topics.sh --describe --under-replicated-partitions \
  --bootstrap-server localhost:9092
```

## Controller 高可用

KRaft 模式下 Controller 通过 Raft 选举，与 Broker 可同节点或分离。

## 消费端高可用

- Consumer Group 自动 rebalance
- `session.timeout.ms` / `heartbeat.interval.ms` 合理配置
- 幂等消费 + 死信队列

## 检查清单

- [ ] replication.factor ≥ 3
- [ ] min.insync.replicas ≥ 2
- [ ] 禁止 unclean leader election
- [ ] 监控 URP、Offline Partitions
- [ ] 跨 AZ/rack 分配副本（`broker.rack` + `replica.selector.class`）

**没有 ISR 保障的 acks=1，不等于高可用**。
