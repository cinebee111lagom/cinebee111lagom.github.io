---
title: nvidia-smi SRE 告警规则与值班手册
date: 2026-08-25 12:00:00
tags:
  - nvidia-smi
  - SRE
  - 告警
categories:
  - nvidia-smi SRE
---

GPU 告警以 **DCGM/Prometheus 为主**，smi 脚本与 node 级检查为补充。

## P0 告警

```yaml
- alert: GPUNodeDown
  expr: up{job="dcgm-exporter"} == 0
  for: 5m

- alert: GPUCountMismatch
  expr: DCGM_FI_DEV_COUNT != on(instance) gpu_expected_count
  for: 2m

- alert: GPUECCUncorrected
  expr: increase(DCGM_FI_DEV_ECC_UNCORRECT_ERR_TOTAL[5m]) > 0
  for: 0m

- alert: GPUXIDDetected
  expr: increase(gpu_xid_errors_total[5m]) > 0
  for: 0m
```

`gpu_xid_errors_total` 可由 node 脚本解析 dmesg 或 DCGM 策略导出。

## P1 告警

```yaml
- alert: GPUTemperatureHigh
  expr: DCGM_FI_DEV_GPU_TEMP > 85
  for: 10m

- alert: GPUMemoryHigh
  expr: DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_FREE > 0.95
  for: 15m

- alert: GPUPowerThrottle
  expr: DCGM_FI_DEV_CLOCKS_EVENT_REASONS > 0
  for: 10m

- alert: GPULowUtilizationPool
  expr: avg(DCGM_FI_DEV_GPU_UTIL) by (pool) < 10
  for: 7d
  # 容量信号，非紧急
```

## smi 脚本兜底告警

```bash
# gpu-check.sh exit 1 → 触发 webhook
if ! nvidia-smi &>/dev/null; then
  curl -X POST "$ALERT_WEBHOOK" -d '{"text":"nvidia-smi failed on '"$(hostname)"'"}'
  exit 1
fi
```

## 值班 Runbook

| 告警 | 第一步 | 第二步 |
|------|--------|--------|
| GPUNodeDown | ssh `nvidia-smi` | 查 exporter / 驱动 / 掉卡 Runbook |
| ECC Uncorrected | cordon 节点 | RMA，迁移作业 |
| XID | dmesg 查 XID 码 | 重启或下线 |
| 显存高 | smi 查进程 | 进程治理 Runbook |
| 高温 | 查风扇/机房 | 降功耗或迁移 |

## 通知

```
P0 → 电话 + IM（5 分钟响应）
P1 → IM + 工单（30 分钟）
```

## 反模式

- 仅监控温度不监控 XID/ECC
- 告警无 Runbook 链接
- staging 与 prod 共用路由导致疲劳

每季度用 **故障注入**（cordon + 模拟 smi 失败）验证告警可达。
