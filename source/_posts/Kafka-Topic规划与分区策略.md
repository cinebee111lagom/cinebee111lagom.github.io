---
title: Kafka Topic 规划与分区策略
date: 2026-08-16 12:15:00
tags:
  - Kafka
  - Topic
  - 分区
categories:
  - Kafka SRE
---

Topic 与分区设计影响吞吐、顺序性与运维复杂度，上线前需评审。

## 命名规范

```
<domain>.<entity>.<event>
例：orders.payment.completed
     logs.app.access
```

- 小写、点分隔
- 环境前缀可选：`prod.orders.payment`

## 分区数

```
分区数 = max(目标吞吐/单分区吞吐, 消费者并行度)
```

| 因素 | 建议 |
|------|------|
| 顺序性 | 同 key 同分区 |
| 并行度 | 分区 ≥ 消费者数 |
| 文件句柄 | 单 Broker 分区数 < 4000 |
| 扩分区 | 提前规划，扩后 key 分布变 |

## 副本与 Retention

```bash
kafka-topics.sh --create --topic orders \
  --partitions 12 --replication-factor 3 \
  --config min.insync.replicas=2 \
  --config retention.ms=604800000 \
  --config compression.type=lz4
```

## 分区键

```java
// 订单 ID 保证同订单有序
producer.send(new ProducerRecord<>("orders", orderId, payload));
```

- 热点 key → 某分区 Lag 高 → 考虑 salt
- null key → round-robin

## 内部 Topic

| Topic | 副本因子 |
|-------|----------|
| __consumer_offsets | 3 |
| __transaction_state | 3 |
| _schemas（Schema Registry） | 3 |

## Compact vs Delete

```properties
cleanup.policy=delete        # 日志、事件流
cleanup.policy=compact       # KV、changelog
cleanup.policy=compact,delete  # 混合
```

## 变更流程

1. 开发提交 Topic 申请（吞吐、Retention、顺序）
2. SRE 评审分区数与副本
3. GitOps / Topic Operator 创建
4. ACL 绑定

## 检查清单

- [ ] 命名符合规范
- [ ] replication.factor=3
- [ ] min.insync.replicas=2
- [ ] Retention 符合合规
- [ ] 无测试 Topic 遗留生产

**分区只能增不能减**，规划宜保守略留余量。
