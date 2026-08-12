---
title: Flink 状态后端与 RocksDB 调优
date: 2026-08-18 10:30:00
tags:
  - Flink
  - RocksDB
  - State
categories:
  - Flink SRE
---

生产大状态作业几乎都用 **EmbeddedRocksDBStateBackend**，SRE 需掌握内存与 I/O 调优。

## 后端选择

| 后端 | 状态上限 | 场景 |
|------|----------|------|
| HashMapStateBackend | TM 内存 | < 几 GB、测试 |
| EmbeddedRocksDBStateBackend | 磁盘 | 生产默认 |

```yaml
state.backend: rocksdb
state.backend.incremental: true
state.backend.rocksdb.localdir: /data/flink/rocksdb
```

## 内存分配

```
TM 总内存
├── JVM Heap（框架 + 网络）
├── Managed Memory（RocksDB block cache + index）
├── Network Memory
└── RocksDB 写缓冲（native，在 managed 外部分配）
```

```yaml
taskmanager.memory.process.size: 16384m
taskmanager.memory.managed.fraction: 0.4
state.backend.rocksdb.block.cache-size: 512mb
state.backend.rocksdb.writebuffer.size: 128mb
state.backend.rocksdb.writebuffer.count: 4
```

## 增量 Checkpoint

```yaml
state.backend.incremental: true
```

只上传变更 SST，大状态 Checkpoint 从小时级降到分钟级。

## State TTL

```java
StateTtlConfig ttl = StateTtlConfig
    .newBuilder(Time.days(7))
    .setUpdateType(StateTtlConfig.UpdateType.OnCreateAndWrite)
    .cleanupFullSnapshot()
    .build();
```

SRE 与开发对齐 TTL，避免状态无限增长。

## 大状态排查

```bash
# Web UI → Job → Task Managers → State Size
# 或 REST
curl http://jm:8081/jobs/<jobId>/vertices/<vertexId>/subtasks/metrics?get=rocksdb.estimated-live-data-size
```

## 常见问题

| 问题 | 解决 |
|------|------|
| Checkpoint 巨大 | TTL、增量、清理无用 state |
| RocksDB 慢 | SSD、调 block cache |
| TM OOM | 减 heap、增 managed、检查全量 WindowFunction |
| 恢复慢 | 增量 + 并行 restore |

## 检查清单

- [ ] 状态 > 10GB 必 RocksDB
- [ ] 增量 Checkpoint 开启
- [ ] localdir 独立 SSD
- [ ] State TTL 有文档
- [ ] 监控 state size 趋势

状态是 Flink 运维的**隐形磁盘与内存消耗者**。
