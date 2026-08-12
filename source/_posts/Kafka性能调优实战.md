---
title: Kafka 性能调优实战
date: 2026-08-16 11:15:00
tags:
  - Kafka
  - 性能调优
categories:
  - Kafka SRE
---

Kafka 性能调优分 Producer、Broker、Consumer 三段，需压测验证。

## Producer 调优

```properties
batch.size=65536
linger.ms=10
compression.type=lz4
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
buffer.memory=67108864
```

- **linger.ms + batch.size**：攒批提高吞吐
- **idempotence**：幂等，防重复

## Broker 调优

```properties
num.io.threads=16
num.network.threads=8
socket.send.buffer.bytes=1048576
replica.fetch.max.bytes=1048576
log.segment.bytes=1073741824
compression.type=lz4
```

磁盘：**顺序写 SSD**，避免与 OS 争 I/O。

## Consumer 调优

```properties
fetch.min.bytes=1048576
fetch.max.wait.ms=500
max.partition.fetch.bytes=10485760
enable.auto.commit=false
```

手动 commit 保证 at-least-once 语义可控。

## 分区数规划

```
目标吞吐 / 单分区吞吐 ≈ 分区数
单分区写入 ~ 10 MB/s（视消息大小）
```

分区过多 → 文件句柄、选举、元数据开销。

## 压测工具

```bash
kafka-producer-perf-test.sh --topic perf \
  --num-records 10000000 --record-size 1024 \
  --throughput -1 --producer-props bootstrap.servers=localhost:9092 \
  acks=all

kafka-consumer-perf-test.sh --topic perf \
  --messages 10000000 --bootstrap-server localhost:9092
```

## 瓶颈定位

| 症状 | 可能瓶颈 |
|------|----------|
| 生产延迟高 | acks、ISR 慢、磁盘 |
| 消费慢 | 业务逻辑、下游、fetch 小 |
| Broker CPU 高 | 压缩、过多分区、副本同步 |
| 网络打满 | 跨 AZ 复制、副本多 |

## 调优流程

1. 基线压测（prod-like 消息大小）
2. 单变量调整
3. 监控 P99 延迟 + 吞吐
4. 文档化最终配置

性能与 durability 常冲突，**acks=all + min.insync.replicas=2 是生产底线**。
