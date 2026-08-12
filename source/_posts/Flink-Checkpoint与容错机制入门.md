---
title: Flink Checkpoint 与容错机制入门
date: 2026-08-17 10:45:00
tags:
  - Flink
  - Checkpoint
  - 容错
categories:
  - Flink 新手入门
---

Checkpoint 是 Flink **容错**的核心：定期快照状态，故障时从最近 Checkpoint 恢复。

## 工作原理

```
1. JobManager 触发 Checkpoint
2. Source 插入 barrier 到数据流
3. 各算子收到 barrier 时 snapshot 状态
4. 全部完成 → Checkpoint 成功
5. 故障 → 从最近成功 Checkpoint 重启
```

## 开启 Checkpoint

```java
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

env.enableCheckpointing(60000);  // 每 60s
env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);
env.getCheckpointConfig().setMinPauseBetweenCheckpoints(30000);
env.getCheckpointConfig().setCheckpointTimeout(600000);
env.getCheckpointConfig().setMaxConcurrentCheckpoints(1);
env.getCheckpointConfig().setExternalizedCheckpointCleanup(
    ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION
);
```

## 状态后端与存储

```java
env.setStateBackend(new EmbeddedRocksDBStateBackend());
env.getCheckpointConfig().setCheckpointStorage("hdfs:///flink/checkpoints");
// 或 s3://bucket/flink-checkpoints
```

## 语义级别

| 语义 | 说明 |
|------|------|
| At-Most-Once | 可能丢 |
| At-Least-Once | 可能重复 |
| Exactly-Once | 不丢不重（Checkpoint + 两阶段提交 Sink） |

## Source/Sink 对齐

```
Kafka Source（offset）+ Flink State + Kafka Sink（事务）
→ 端到端 Exactly-Once
```

## 重启策略

```java
env.setRestartStrategy(RestartStrategies.fixedDelayRestart(
    3, Time.seconds(10)  // 最多 3 次，间隔 10s
));
```

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| Checkpoint 超时 | 状态大、磁盘慢 | 增大 timeout、RocksDB |
| 对齐慢 | 反压、数据倾斜 | 调并行度、缓冲 |
| 恢复慢 | Checkpoint 过大 | 增量 Checkpoint、TTL |
| 频繁失败 | TM 内存不足 | 加内存、调 managed memory |

## 本地观察 Checkpoint

Web UI → Running Jobs → Checkpoints 标签页，查看 duration、size、alignment。

**新手建议**：开发环境先开 Checkpoint 60s，用 `print` Sink 时可关；接 Kafka 生产必须开。
