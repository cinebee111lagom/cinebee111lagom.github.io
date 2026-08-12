---
title: Flink 反压诊断与性能调优 SRE 实践
date: 2026-08-18 11:15:00
tags:
  - Flink
  - 反压
  - 性能
categories:
  - Flink SRE
---

反压是 Flink 性能问题最常见信号，SRE 需系统诊断而非盲目加资源。

## 诊断流程

```
1. Web UI → Back Pressure（OK/LOW/HIGH）
2. 找到第一个 HIGH 的上游算子
3. 看 Metrics：busyTime vs backPressuredTime
4. 区分：计算慢 vs Sink 慢 vs 数据倾斜
5. 针对性优化
```

## Sink 瓶颈（最常见）

```java
// JDBC 批量
JdbcExecutionOptions.builder()
    .withBatchSize(500)
    .withBatchIntervalMs(2000)
    .build()

// Kafka Sink 提高并行度
sink.setParallelism(16);
```

## 数据倾斜

```
症状：某 subtask Records 远高于其他
```

- 加盐 key 两阶段聚合
- `rebalance()` 打散（仅无 key 场景）
- 自定义 Partitioner

## Checkpoint 与性能

| 现象 | 调优 |
|------|------|
| Checkpoint 期间反压 | 增 min-pause、unaligned checkpoint |
| 对齐慢 | `execution.checkpointing.unaligned: true` |
| 状态大 | 增量 + RocksDB 调优 |

```yaml
execution.checkpointing.unaligned: true
execution.checkpointing.alignment-timeout: 30s
```

## 并行度调整

```bash
# 需 savepoint rescale
flink run -s <savepoint> -p 32 job.jar
```

Source 并行度 ≤ Kafka 分区数。

## 压测基线

| 指标 | 记录 |
|------|------|
| 峰值 records/s | 压测报告 |
| P99 端到端延迟 | 含 Sink |
| Checkpoint 耗时/大小 | 稳态与峰值 |
| 反压状态 | 应 OK |

## SRE Checklist

- [ ] 反压算子已文档化
- [ ] Sink 批量参数已调优
- [ ] 无热点 subtask（Web UI 均衡）
- [ ] Checkpoint 不触发连锁反压
- [ ] 季度压测复验容量

**加 TM 前先消除 Sink 与倾斜**，否则只是浪费资源。
