---
title: Kafka 容量规划与基准测试
date: 2026-08-16 13:30:00
tags:
  - Kafka
  - 容量规划
  - 压测
categories:
  - Kafka SRE
---

容量规划需在上线前通过基准测试验证 Broker 数、分区数与磁盘/network 上限。

## 容量估算

| 维度 | 公式/参考 |
|------|-----------|
| 磁盘 | 日写入 × Retention × 1.2 / Broker 数 |
| 网络 | 峰值 MB/s × RF × 1.5（副本同步） |
| Broker 数 | 总分区数 / 2000（单 Broker 分区上限参考） |
| 分区数 | 峰值吞吐 / 10 MB/s per partition |

## 基准测试

### Producer 压测

```bash
kafka-producer-perf-test.sh \
  --topic perf-test \
  --num-records 50000000 \
  --record-size 1024 \
  --throughput -1 \
  --producer-props \
    bootstrap.servers=10.0.1.11:9092 \
    acks=all \
    linger.ms=10 \
    batch.size=65536 \
    compression.type=lz4
```

记录：`999thPercentile latency`、`MB/sec`。

### Consumer 压测

```bash
kafka-consumer-perf-test.sh \
  --topic perf-test \
  --messages 50000000 \
  --bootstrap-server 10.0.1.11:9092 \
  --threads 4
```

### 端到端延迟

使用 OpenMessaging Benchmark 或自定义 timestamp header 测量 produce → consume 延迟。

## 扩容触发条件

| 信号 | 动作 |
|------|------|
| 磁盘 > 70% | 扩 Retention offload 或加盘 |
| CPU > 70% 持续 | 加 Broker |
| 网络 > 60% | 加 Broker 或压缩 |
| 单 Broker 分区 > 3000 |  rebalance |
| Lag 常态高 | 扩消费者/分区 |

## 容量报告模板

```
集群：prod-kafka
Broker：5 × 8C32G + 2TB SSD
峰值：120 MB/s 写入，80 MB/s 读取
分区：1200
Retention：7 天
余量：磁盘 45%，CPU 55%
结论：Q4 前需 +2 Broker
```

## 检查清单

- [ ] 上线前压测达预期 SLA
- [ ] 峰值 2× 余量
- [ ] 季度容量 review
- [ ] 大促前专项压测
- [ ] 扩容流程文档化

**没有压测的容量规划是猜的**。
