---
title: Kafka 部署架构选型指南
date: 2026-08-16 09:15:00
tags:
  - Kafka
  - 架构
categories:
  - Kafka SRE
---

Kafka 架构选型需结合吞吐、延迟、运维能力与合规要求。

## 常见架构

| 架构 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| 单集群多 Topic | 中小规模 | 简单 | 故障影响面大 |
| 多集群按域拆分 | 大型组织 | 隔离 blast radius | 跨集群复制复杂 |
| KRaft 模式 | 新部署推荐 | 去 ZooKeeper、简化运维 | 需 Kafka 3.3+ |
| ZooKeeper 模式 | 存量集群 | 成熟 | ZK 额外运维 |
| 云 MSK / Confluent Cloud | 免运维 | 托管监控/备份 | 成本、定制受限 |

## 副本与 ISR

```
Topic partition → Leader + Follower(s)
replication.factor = 3
min.insync.replicas = 2
```

- **acks=all**：写入 ISR 多数派才确认
- **unclean.leader.election=false**：禁止非 ISR 选主（防数据丢失）

## 选型决策树

```
峰值吞吐 < 100 MB/s？
  ├─ 是 → 3~5 Broker KRaft 集群
  └─ 否 → 是否跨 Region 读？
           ├─ 是 → 多集群 + MirrorMaker 2
           └─ 否 → 水平扩 Broker + 增加分区
```

## 存储选型

| 类型 | 场景 |
|------|------|
| 本地 SSD | 低延迟、高 IOPS（推荐） |
| EBS / 云盘 | K8s、弹性扩容 |
| Tiered Storage | 冷数据 offload 到 S3 |

## 版本选择

- 新集群推荐 **Kafka 3.6+ KRaft**
- 客户端与 Broker 版本差不超过 2 个大版本

架构文档应包含：Broker 拓扑、Controller 节点、Topic 规划、Retention 策略、容灾方案。
