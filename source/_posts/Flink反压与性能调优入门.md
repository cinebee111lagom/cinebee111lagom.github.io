---
title: Flink 反压与性能调优入门
date: 2026-08-17 12:30:00
tags:
  - Flink
  - 反压
  - 性能
categories:
  - Flink 新手入门
---

反压（Backpressure）是下游处理不过来时上游自动降速，理解它是调优的第一步。

## 什么是反压

```
Source → Map → Window → Sink(DB 慢)
                ↑
         Sink 消费慢 → Window 积压 → Map 反压 → Source 减速
```

Web UI → Job → Back Pressure 显示 **OK / LOW / HIGH**。

## 定位瓶颈

1. Web UI 看哪个算子 HIGH 反压
2. Metrics 看 `busyTimeMsPerSecond`、`backPressuredTimeMsPerSecond`
3. 检查 Sink 是否外部系统慢（DB、ES、Kafka）

## 常见优化

| 瓶颈 | 优化 |
|------|------|
| Sink 慢 | 批量写、异步 IO、提高 Sink 并行度 |
| 窗口聚合慢 | 用 AggregateFunction、预聚合 |
| 序列化慢 | Avro/Protobuf 替代 JSON |
| 状态大 | RocksDB、State TTL、增量 Checkpoint |
| 数据倾斜 | 加盐、rebalance、自定义分区 |

## 对象重用（谨慎）

```java
env.getConfig().enableObjectReuse();  // 减少 GC，需保证不篡改对象
```

## 链式（Chaining）

```java
// 默认相邻算子 chain 减少序列化
env.disableOperatorChaining();  // 调试时可关
```

## 缓冲区

```yaml
taskmanager.network.memory.fraction: 0.1
taskmanager.network.memory.min: 64mb
taskmanager.network.memory.max: 1gb
```

## 监控指标

| 指标 | 含义 |
|------|------|
| numRecordsInPerSecond | 输入速率 |
| numRecordsOutPerSecond | 输出速率 |
| checkpointDuration | Checkpoint 耗时 |
| lastCheckpointSize | 状态大小 |

## 压测方法

1. 用 datagen 或 kafka-producer-perf-test 灌数据
2. 逐步升并行度观察吞吐 plateau
3. 记录 CPU、内存、反压、延迟

## 新手 checklist

- [ ] 反压算子已定位
- [ ] Sink 批量参数已调
- [ ] Checkpoint 不超时
- [ ] 无严重数据倾斜
- [ ] GC 日志无频繁 Full GC

**先消除反压，再谈调并行度**。
