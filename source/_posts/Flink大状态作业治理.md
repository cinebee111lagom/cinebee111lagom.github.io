---
title: Flink 大状态作业治理
date: 2026-08-18 12:30:00
tags:
  - Flink
  - 大状态
categories:
  - Flink SRE
---

状态超过 **50GB** 的作业需专项治理，否则 Checkpoint 与恢复成为运维噩梦。

## 风险信号

| 信号 | 阈值 |
|------|------|
| Checkpoint size | > 20GB |
| Checkpoint duration | > 10min |
| State backend 磁盘 | 单 TM > 100GB |
| 恢复时间 | > 30min |

## 治理手段

### 1. State TTL

```java
StateTtlConfig.newBuilder(Time.days(3)).cleanupFullSnapshot().build();
```

### 2. 增量 Checkpoint

```yaml
state.backend.incremental: true
```

### 3. 状态拆分

```
单作业 200GB → 拆为 2 作业 + 不同 key 范围
```

### 4. 外部状态

- 热数据 Flink State
- 冷数据异步写 Redis/HBase，查询 Lookup

### 5. RocksDB 调优

见《状态后端与 RocksDB 调优》篇。

## 审批流程

```
新作业 state 预估 > 50GB
  → 架构评审（TTL、拆分、增量）
  → staging 压测 Checkpoint
  → 生产上线 + 专项监控
```

## 监控专项

```promql
flink_job_lastCheckpointSize
flink_job_lastCheckpointDuration
rocksdb_estimated_live_data_size
```

## 应急

| 场景 | 动作 |
|------|------|
| Checkpoint 连续失败 | 临时增 timeout、减 interval |
| 磁盘满 | TTL 缩短、savepoint 缩并行度 |
| 不可恢复 | 最后 savepoint + 状态重建方案 |

## 检查清单

- [ ] 大状态作业有 owner 与文档
- [ ] TTL 已配置
- [ ] 增量 Checkpoint 开启
- [ ] 季度 savepoint restore 演练
- [ ] 拆分/降级预案

**状态越大，运维成本指数上升**，架构阶段就要控。
