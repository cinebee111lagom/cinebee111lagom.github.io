---
title: Ceph SRE 告警规则与值班手册
date: 2026-08-31 10:15:00
tags:
  - Ceph
  - SRE
  - 告警
categories:
  - Ceph SRE
---

## P0 告警

```yaml
- alert: CephHealthError
  expr: ceph_health_status == 2
  for: 5m

- alert: CephMonQuorumAtRisk
  expr: ceph_mon_quorum_status < 1
  for: 2m

- alert: CephOSDDown
  expr: count(ceph_osd_up == 0) > 0
  for: 5m

- alert: CephClusterFull
  expr: ceph_cluster_total_used_bytes / ceph_cluster_total_bytes > 0.90
  for: 5m
```

## P1 告警

```yaml
- alert: CephHealthWarn
  expr: ceph_health_status == 1
  for: 30m

- alert: CephOSDNearFull
  expr: max(ceph_osd_utilization) > 0.80
  for: 15m

- alert: CephPGDegraded
  expr: ceph_pg_degraded > 0
  for: 30m

- alert: CephSlowOps
  expr: rate(ceph_osd_slow_ops[5m]) > 0
  for: 15m

- alert: CephPGStuck
  expr: ceph_pg_stuck > 0
  for: 15m
```

## 值班 Runbook

| 告警 | 第一步 | 第二步 |
|------|--------|--------|
| HEALTH_ERR | health detail | PG/OSD 日志 |
| OSD Down | ceph osd tree | 磁盘/smart/重启 |
| NearFull | osd df tree | 扩容/删快照/清 RGW |
| Degraded | ceph -s | 等 recovery 或修 OSD |
| Slow ops | osd perf | 磁盘/网络/负载 |

## 通知

```
P0 → 电话 + IM（5 分钟）
P1 → IM + 工单（30 分钟）
recovery 中 WARN → 仅 IM（避免疲劳）
```

## 反模式

- degraded 告警阈值 0 分钟（recovery 误报）
- 无 Runbook 链接
- 不区分 planned maintenance

每季度 **OSD out 演练** 验证告警链路。
