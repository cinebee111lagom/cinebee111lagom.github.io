---
title: Kafka SRE 入门：生产部署职责与目标
date: 2026-08-16 09:00:00
tags:
  - Kafka
  - SRE
categories:
  - Kafka SRE
---

Kafka 是事件流与消息队列的核心基础设施，SRE 目标是让它在**可用性、吞吐、延迟**之间长期稳定运行。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | 架构选型、Broker 安装、KRaft/ZK 集群 |
| 高可用 | 副本因子、ISR、Controller 选举 |
| 容量 | 分区数、磁盘、网络带宽、Retention |
| 可观测 | Lag、吞吐、Under-Replicated Partitions |
| 变更 | 升级、扩缩容、Topic 变更 |
| 安全 | SASL、SSL、ACL、审计 |
| 容灾 | MirrorMaker 2、跨 Region 复制 |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| 可用性 | 99.95% ~ 99.99% |
| 生产 P99 延迟 | < 10ms（同 AZ） |
| 消费 Lag | 常态 < 1 分钟，峰值可容忍 |
| RPO | 取决于副本 + MM2，通常 ≤ 分钟级 |
| RTO | Broker 故障自动恢复 ≤ 5 分钟 |

## 架构演进路径

```
单 Broker → 多 Broker 集群 → KRaft 模式（去 ZK）
         → Schema Registry + Connect
         → 多集群 + MirrorMaker 2 容灾
         → K8s Strimzi / 云托管 MSK/Confluent Cloud
```

## 与开发、平台的边界

- **开发**：Topic 设计、消息格式、分区键、消费幂等
- **SRE**：集群部署、监控、扩容、升级、ACL
- **数据平台**：Connect、Flink/Spark 集成

本系列 20 篇覆盖 Kafka 从部署、HA、监控、Lag 治理到容灾演练的完整 SRE 路径。
