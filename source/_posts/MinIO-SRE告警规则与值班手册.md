---
title: MinIO SRE 告警规则与值班手册
date: 2026-09-02 10:15:00
tags:
  - MinIO
  - SRE
  - 告警
categories:
  - MinIO SRE
---

## P0 告警

```yaml
- alert: MinIOClusterDown
  expr: up{job="minio-cluster"} == 0
  for: 5m

- alert: MinIOHealthCritical
  expr: minio_cluster_health_status == 0
  for: 5m

- alert: MinIODiskOffline
  expr: minio_cluster_drive_offline_total > 0
  for: 10m

- alert: MinIOClusterReadOnly
  expr: minio_cluster_usage_total_bytes / minio_cluster_capacity_raw_total_bytes > 0.95
  for: 5m
```

## P1 告警

```yaml
- alert: MinIOCapacityLow
  expr: minio_cluster_capacity_usable_free_bytes / minio_cluster_capacity_usable_total_bytes < 0.15
  for: 30m

- alert: MinIOHigh5xxRate
  expr: rate(minio_s3_requests_total{code="5xx"}[5m]) / rate(minio_s3_requests_total[5m]) > 0.01
  for: 10m

- alert: MinIOHealBacklog
  expr: minio_heal_objects_heal_total > 100000
  for: 1h

- alert: MinIOReplicationLag
  expr: minio_cluster_replication_lag_seconds > 900
  for: 15m
```

## 值班 Runbook

| 告警 | 第一步 | 第二步 |
|------|--------|--------|
| ClusterDown | LB/节点进程 | `mc admin info` |
| CapacityLow | Top bucket | lifecycle/扩容 |
| DiskOffline | 硬件 SMART | 换盘/heal |
| 5xx 高 | 日志/metrics | 磁盘/网络 |
| Repl lag | `mc replicate backlog` | 网络/目标集群 |

## 通知

```
P0 → 电话 + IM（5 分钟）
P1 → IM + 工单（30 分钟）
```

## 反模式

- heal 期间 degraded 误报 P0 无抑制
- 无 Runbook 链接

每季度 **节点+磁盘故障演练**。
