---
title: 阿里云消息队列 Kafka/RocketMQ 运维
date: 2026-08-26 12:45:00
tags:
  - 阿里云
  - Kafka
  - RocketMQ
categories:
  - 阿里云资源 SRE
---

阿里云托管消息队列降低 Kafka/RocketMQ 运维负担，SRE 仍需监控容量与 ACL。

## 产品选型

| 产品 | 适用 |
|------|------|
| 消息队列 Kafka 版 | Kafka 生态、Flink 集成 |
| 消息队列 RocketMQ 版 | 阿里系、事务消息 |
| RabbitMQ 版 | AMQP 协议 |

## Kafka 版生产配置

```
实例类型：专业版（高可用）
存储：按峰值保留 7 天估算
Topic：replication ≥ 3（专业版默认）
跨 AZ：开启
```

## 网络

```
VPC 私网接入
SASL 用户 + ACL
禁止公网
```

## 监控告警

| 指标 | 告警 |
|------|------|
| 磁盘使用率 | > 80% P1 |
| 消费延迟 | > 阈值 P1 |
| 实例连接数 | > 80% P2 |

## 与自建 Kafka 差异

| 项 | 托管 | 自建 ECS/ACK |
|----|------|--------------|
| 运维 | 阿里云 | 见 Kafka SRE 系列 |
| 扩容 | 控制台升配 | 手动扩 Broker |
| 版本 | 控制台升级 | 自行滚动 |

## RocketMQ 要点

```
Group 消费进度监控
死信队列 DLQ 告警
消息轨迹排查
```

## 变更

- 升配：低峰窗口，评估消费 lag
- Topic 扩容：分区只增不减

与 **Kafka SRE** 系列互补：托管侧重控制台与云监控，自建侧重 KRaft/Patroni 等。
