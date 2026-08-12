---
title: Flink 并行度与资源配置入门
date: 2026-08-17 12:15:00
tags:
  - Flink
  - 并行度
  - 资源配置
categories:
  - Flink 新手入门
---

并行度决定 Flink 作业的**并发能力**，合理配置是性能与成本的关键。

## 并行度层次

```
作业默认并行度（env.setParallelism）
  ↓ 可被算子级覆盖
Source / Operator / Sink 各自并行度
```

```java
env.setParallelism(4);
stream.map(...).setParallelism(8);
kafkaSource.setParallelism(3);  // 通常 = Kafka 分区数
```

## 与 Kafka 分区关系

```
Kafka Topic 12 分区 → Source 并行度建议 ≤ 12
                      → 超出部分 subtask 空闲
```

## Slot 与 TaskManager

```
TaskManager (8GB, 4 slots)
  ├─ Slot 1: subtask A, subtask B（可共享）
  ├─ Slot 2: ...
  
集群总并行度上限 ≈ 所有 TM 的 slot 数之和
```

## 提交参数

```bash
./bin/flink run -p 8 \
  -Dtaskmanager.memory.process.size=4096m \
  -Dtaskmanager.numberOfTaskSlots=4 \
  my-job.jar
```

## 内存（Flink 1.19+）

```yaml
# flink-conf.yaml
taskmanager.memory.process.size: 4096m
taskmanager.memory.managed.fraction: 0.4   # RocksDB 等
```

## 如何定并行度

| 因素 | 建议 |
|------|------|
| CPU 密集 | ≈ CPU 核数 |
| I/O 密集 | 2~4 × 核数 |
| Kafka Source | = 分区数 |
| 全局聚合（单 key） | 无法并行，瓶颈在 keyBy |

## 数据倾斜

```
某 key 数据量极大 → 单个 subtask 慢 → 反压
解决：加盐 key、两阶段聚合、Local-Global 聚合
```

## Web UI 观察

Running Jobs → Task Managers → 看每个 subtask 的 Records Sent/Received 是否均衡。

## 新手默认

- 本地：`setParallelism(1)` 方便调试
- 测试集群：`4~8`
- 生产：压测后定，Source 对齐 Kafka 分区

并行度不是越大越快，**瓶颈算子 + 倾斜**才是调优重点。
