---
title: Flink 与 Kafka 端到端 Exactly-Once 运维
date: 2026-08-18 12:45:00
tags:
  - Flink
  - Kafka
  - Exactly-Once
categories:
  - Flink SRE
---

Flink + Kafka 是实时链路标配，Exactly-Once 需 Source、Checkpoint、Sink 三段对齐。

## 架构

```
Kafka Source (offset) → Flink State → Kafka Sink (2PC 事务)
         ↓ Checkpoint  barrier 对齐
         ↓ offset 写入 state + 提交 Kafka 事务
```

## Source 配置

```java
KafkaSource.builder()
    .setStartingOffsets(OffsetsInitializer.committedOffsets())
    .build();
// Checkpoint 时提交 offset 到 state
```

## Sink 配置

```java
KafkaSink.builder()
    .setDeliveryGuarantee(DeliveryGuarantee.EXACTLY_ONCE)
    .setTransactionalIdPrefix("flink-orders-")
    .build();
```

## 必开 Checkpoint

```yaml
execution.checkpointing.interval: 60000
execution.checkpointing.mode: EXACTLY_ONCE
```

## Kafka 侧参数

```properties
transaction.max.timeout.ms=900000    # > checkpoint interval × 2
min.insync.replicas=2
acks=all
```

## 运维验证

```bash
# 1. 作业运行中 kill TM，重启后无重复无丢（对账）
# 2. 消费目标 topic，count 与源对账
# 3. 检查 __transaction_state topic
```

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 事务超时 | checkpoint 太慢 | 调 interval/timeout |
| 重复消息 | at-least-once 降级 | 查 checkpoint 失败日志 |
| 消费卡住 | transactionalId 冲突 | 前缀唯一、旧实例释放 |
| Lag 高 | Flink 反压 | 见反压篇 |

## 降级策略

```
Exactly-Once 失败 → 临时 at-least-once + 下游幂等
                  → 修复后恢复 EOS
```

## 检查清单

- [ ] Checkpoint 成功率 > 99%
- [ ] transactionalIdPrefix 作业唯一
- [ ] Kafka RF=3, min.insync.replicas=2
- [ ] 对账 job 定期跑
- [ ] 与 Kafka SRE 联合 on-call

Exactly-Once 是**配置 + 运维**共同保障，非默认自动达成。
