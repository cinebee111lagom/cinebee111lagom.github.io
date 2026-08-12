---
title: Kafka 消费延迟与 Lag 治理
date: 2026-08-16 11:00:00
tags:
  - Kafka
  - Lag
  - 消费
categories:
  - Kafka SRE
---

Consumer Lag 是 Kafka SRE 最常见的生产问题，治理需从分区、消费能力与下游依赖入手。

## Lag 含义

```
Lag = Log End Offset - Current Offset（按 partition）
```

Group 总 Lag = 各分区 Lag 之和。

## 常见原因

| 原因 | 现象 | 方案 |
|------|------|------|
| 消费者不足 | 部分 partition Lag 高 | 增加实例（≤ 分区数） |
| 消费慢 | 全部分区均匀 Lag | 优化逻辑、批处理 |
| 下游 DB 慢 | 消费阻塞 | 限流、异步写、扩容 DB |
| Rebalance 风暴 | Lag 周期性尖刺 | 调 session/heartbeat |
| 生产突增 | Lag 整体上升 | 扩容消费者、限生产 |

## 排查命令

```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group order-consumer --members --verbose

kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group order-consumer --offsets
```

## 消费者参数

```properties
max.poll.records=500
max.poll.interval.ms=300000
fetch.min.bytes=1048576
fetch.max.wait.ms=500
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

## 分区与并行度

```
消费者实例数 ≤ Topic 分区数
要 2× 并行 → 先 double 分区（不可逆需谨慎）
```

扩分区后需重新规划 key 分布。

## 死信队列（DLQ）

```java
// 消费失败 N 次 → 写入 orders.DLT
// 避免 poison pill 阻塞全 partition
```

## SRE 治理流程

1. 按 Group 设置 Lag 基线与告警
2. 区分「可延迟」（日志）与「不可延迟」（订单）
3. 峰值前压测消费吞吐
4. 临时 Lag：临时扩容 + 事后缩容

## 检查清单

- [ ] 核心 Group Lag 监控 + 告警
- [ ] 消费者数与分区数匹配
- [ ] Rebalance 日志无异常
- [ ] DLQ 有监控
- [ ] 峰值容量预案

**加 Broker 不能降 Lag，加消费者才能**。
