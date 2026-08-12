---
title: Kafka 生产参数基线
date: 2026-08-16 10:00:00
tags:
  - Kafka
  - 参数调优
categories:
  - Kafka SRE
---

Kafka Broker 参数需按硬件与 workload 调整，以下为 8 核 32GB + SSD 基线参考。

## 网络与线程

```properties
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=1048576
socket.receive.buffer.bytes=1048576
socket.request.max.bytes=104857600
```

## 日志与 Retention

```properties
log.retention.hours=168
log.retention.bytes=-1
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
compression.type=lz4
```

## 副本

```properties
default.replication.factor=3
min.insync.replicas=2
replica.fetch.max.bytes=1048576
num.replica.fetchers=4
```

## 生产吞吐优化

```properties
num.partitions=6
message.max.bytes=1048576
replica.lag.time.max.ms=30000
```

## JVM 堆（Broker）

```bash
KAFKA_HEAP_OPTS="-Xmx6g -Xms6g"
```

- Kafka 依赖页缓存，**堆不宜过大**（通常 ≤ 6GB）
- 使用 G1GC

## 消费者相关（Broker 侧）

```properties
group.initial.rebalance.delay.ms=3000
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
```

## 日志

```properties
log4j.logger.kafka=INFO
log4j.logger.kafka.controller=INFO
log4j.logger.kafka.request.logger=WARN
```

## 调优原则

| 原则 | 说明 |
|------|------|
| 堆小页缓存大 | 顺序写依赖 OS cache |
| 分区数适度 | 过多分区增加文件句柄与选举开销 |
| 压缩选 lz4/zstd | 平衡 CPU 与带宽 |
| 一次改一项 | 压测对比 |

参数变更需滚动重启 Broker，**每次只改一个 Broker 验证**。
