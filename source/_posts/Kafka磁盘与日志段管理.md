---
title: Kafka 磁盘与日志段管理
date: 2026-08-16 12:45:00
tags:
  - Kafka
  - 磁盘
  - 日志
categories:
  - Kafka SRE
---

磁盘是 Kafka 最常见瓶颈，SRE 需规划容量、Retention 与日志段生命周期。

## 磁盘规划

```
所需空间 ≈ 日写入量 × Retention 天数 × 副本因子 / 本地副本数
         + 20% 余量
```

例：500 GB/天 × 7 天 × RF3 / 3 ≈ 3.5 TB（每 Broker）

## log.dirs

```properties
log.dirs=/data/kafka-logs-1,/data/kafka-logs-2
```

- 独立 SSD，与 OS 盘分离
- 多目录可提升并行 I/O

## 日志段

```properties
log.segment.bytes=1073741824
log.roll.ms=604800000
log.retention.hours=168
log.retention.bytes=-1
log.cleanup.policy=delete
```

## 监控

```bash
du -sh /data/kafka-logs/*
kafka-log-dirs.sh --bootstrap-server localhost:9092 \
  --describe --topic-list orders
```

Prometheus：`kafka_log_log_size`、`node_filesystem_avail_bytes`。

## 磁盘满应急

1. 确认 Retention 生效（`log.retention.check.interval.ms`）
2. 临时调低 `log.retention.hours`
3. 删除无业务 Topic
4. 扩容 PVC / 挂载新盘
5. **禁止** rm 活跃 `.log` 文件

## Tiered Storage

```properties
remote.log.storage.system.enable=true
```

热数据本地 SSD，冷数据 S3，降低磁盘压力。

## I/O 优化

- 禁用 swap：`vm.swappiness=1`
- 文件系统：xfs/ext4，noatime
- RAID10 或独立盘优于 RAID5

## 检查清单

- [ ] 磁盘使用率告警 75%/85%
- [ ] Retention 与业务合规对齐
- [ ] log.dirs 独立挂载
- [ ] 定期清理测试 Topic
- [ ] 扩容 Runbook 就绪

**Kafka 不会自动无限存**，Retention 是容量管理第一杠杆。
