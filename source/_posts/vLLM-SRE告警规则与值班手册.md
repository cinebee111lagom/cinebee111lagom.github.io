---
title: vLLM SRE 告警规则与值班手册
date: 2026-09-04 10:15:00
tags:
  - vLLM
  - SRE
  - 告警
categories:
  - vLLM SRE
---

## P0 告警

```yaml
- alert: VllmDown
  expr: up{job="vllm"} == 0
  for: 2m

- alert: VllmHealthFail
  expr: probe_success{job="blackbox-vllm-health"} == 0
  for: 2m

- alert: VllmErrorRateHigh
  expr: |
    sum(rate(http_requests_total{job="vllm-gateway",code=~"5.."}[5m]))
    / sum(rate(http_requests_total{job="vllm-gateway"}[5m])) > 0.05
  for: 5m

- alert: VllmGPUOOMSuspect
  expr: increase(container_oom_events_total{container="vllm"}[10m]) > 0
  for: 0m
```

## P1 告警

```yaml
- alert: VllmHighTTFT
  expr: histogram_quantile(0.99, sum(rate(vllm_time_to_first_token_seconds_bucket[5m])) by (le, model)) > 3
  for: 15m

- alert: VllmQueueBackup
  expr: vllm_num_requests_waiting > 50
  for: 10m

- alert: VllmGPUUtilLow
  expr: avg(DCGM_FI_DEV_GPU_UTIL{gpu_pool="llm"}) < 10
  for: 2h   # 成本信号，非紧急

- alert: VllmGPUMemoryHigh
  expr: DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.98
  for: 10m
```

指标名请按实际 `/metrics` 与 DCGM 调整。

## 值班 Runbook

| 告警 | 第一步 | 第二步 |
|------|--------|--------|
| Down | 查 Pod/进程、事件 | 看 OOM/NCCL 日志 |
| 5xx | 网关 vs 后端 | 降并发或扩容 |
| TTFT 高 | 队列与 GPU util | 降 max_num_seqs / 扩副本 |
| 显存高 | nvidia-smi | 降 max_model_len 或迁走负载 |
| OOM | 重启 + 降配 | 量化/TP/缩并发 |

## 通知

```
P0 → 电话 + IM（5 分钟）
P1 → IM + 工单（30 分钟）
```

## 反模式

- 加载期误报 Down（探针过严）
- 无 model 标签无法定位池
- 告警无 Runbook 链接
