---
title: Flink 生产参数基线
date: 2026-08-18 10:00:00
tags:
  - Flink
  - 参数
categories:
  - Flink SRE
---

Flink 生产参数需按状态规模与 SLA 调整，以下为 Application 模式基线。

## Checkpoint

```yaml
execution.checkpointing.interval: 60000
execution.checkpointing.mode: EXACTLY_ONCE
execution.checkpointing.timeout: 600000
execution.checkpointing.min-pause: 30000
execution.checkpointing.max-concurrent-checkpoints: 1
execution.checkpointing.externalized-checkpoint-retention: RETAIN_ON_CANCELLATION
execution.checkpointing.tolerable-failed-checkpoints: 3
```

## State Backend

```yaml
state.backend: rocksdb
state.backend.incremental: true
state.checkpoints.dir: s3://bucket/flink/checkpoints
state.savepoints.dir: s3://bucket/flink/savepoints
```

## 内存（TM 8GB 示例）

```yaml
taskmanager.memory.process.size: 8192m
taskmanager.memory.managed.fraction: 0.4
taskmanager.memory.network.fraction: 0.1
taskmanager.numberOfTaskSlots: 4
```

## 重启策略

```yaml
restart-strategy: fixed-delay
restart-strategy.fixed-delay.attempts: 3
restart-strategy.fixed-delay.delay: 30s
```

## 网络与反压

```yaml
taskmanager.network.memory.min: 128mb
taskmanager.network.memory.max: 1gb
pipeline.object-reuse: false
```

## 日志

```yaml
env.java.opts: "-Dlog4j.configurationFile=/opt/flink/conf/log4j.properties"
```

## RocksDB 调优（大状态）

```yaml
state.backend.rocksdb.predefined-options: SPINNING_DISK_OPTIMIZED_HIGH_MEM
state.backend.rocksdb.block.cache-size: 256mb
state.backend.rocksdb.writebuffer.size: 64mb
```

## 调优原则

| 原则 | 说明 |
|------|------|
| Checkpoint 间隔 | 平衡 RPO 与性能，通常 1~5 分钟 |
| 堆内存适中 | TM 堆 1~2GB，大状态靠 RocksDB |
| 增量 Checkpoint | 大状态必开 |
| 一次改一项 | 变更后观察 Checkpoint 耗时 |

参数通过 `flink-conf.yaml` 或 `-D` 提交参数覆盖，**变更需 Savepoint 重启验证**。
