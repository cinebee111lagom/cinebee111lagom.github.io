---
title: Flink 容量规划与基准测试
date: 2026-08-18 13:30:00
tags:
  - Flink
  - 容量规划
categories:
  - Flink SRE
---

Flink 容量需结合吞吐、状态、Checkpoint 与 Kafka 分区综合规划。

## 容量维度

| 维度 | 估算 |
|------|------|
| TM 数 | 并行度 / slots per TM |
| TM 内存 | 状态/TM + 网络缓冲 + 堆 1~2GB |
| Checkpoint 存储 | 状态大小 × 保留份数 |
| CPU | I/O 密集：2~4 核/slot |
| Kafka 分区 | Source 并行度上限 |

## 基准测试

```bash
# 生产-like jar + datagen/kafka replay
flink run -p 16 perf-job.jar \
  -Dexecution.checkpointing.interval=60000

# 观察
# - numRecordsInPerSecond plateau
# - backPressure OK
# - checkpointDuration stable
```

## 扩容信号

| 信号 | 动作 |
|------|------|
| 反压 HIGH | 加并行度/TM 或优化 Sink |
| Checkpoint > 5min | RocksDB 调优、增量 CK |
| TM CPU > 80% | 加 TM |
| Kafka Lag 升 | 对齐分区与并行度 |
| State > 规划 | TTL、拆分作业 |

## 容量报告模板

```
作业：orders-realtime
并行度：32，TM：8×4slots，8GB
峰值：50k records/s，1KB/msg
Checkpoint：8GB，90s
Kafka：32 分区
余量：CPU 40%，反压 OK
结论：Q4 峰值需 +4 TM
```

## 成本优化

- 低峰降并行度（savepoint rescale）
- Tiered：小状态作业用小 TM
- Spot 实例跑 TM（需 Checkpoint 容忍）

## 检查清单

- [ ] 上线前压测报告归档
- [ ] 峰值 2× 余量
- [ ] Checkpoint 存储容量规划
- [ ] 季度复测
- [ ] 与 Kafka 容量联动

容量规划是**压测数据驱动**，非拍脑袋加机器。
