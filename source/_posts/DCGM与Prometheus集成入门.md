---
title: DCGM 与 Prometheus 集成入门
date: 2026-08-23 11:00:00
tags:
  - DCGM
  - Prometheus
categories:
  - DCGM 新手入门
---

生产 GPU 监控标准路径：**dcgm-exporter → Prometheus → Grafana**。

## 架构

```
GPU Node
  ├── nv-hostengine（或 exporter 内置）
  ├── dcgm-exporter :9400/metrics
  └── Prometheus scrape

Prometheus → Grafana Dashboard
           → Alertmanager
```

## 部署 dcgm-exporter（Docker）

```bash
docker run -d --name dcgm-exporter --gpus all --cap-add SYS_ADMIN \
  -p 9400:9400 \
  nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04

curl -s localhost:9400/metrics | head -20
```

## Prometheus 配置

```yaml
scrape_configs:
  - job_name: dcgm
    static_configs:
      - targets: ["gpu-node-1:9400", "gpu-node-2:9400"]
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
```

## 常用指标（示例）

```promql
# GPU 利用率
DCGM_FI_DEV_GPU_UTIL

# 显存使用
DCGM_FI_DEV_FB_USED
DCGM_FI_DEV_FB_FREE

# 温度
DCGM_FI_DEV_GPU_TEMP

# 功耗
DCGM_FI_DEV_POWER_USAGE

# XID 错误（需 rate）
rate(DCGM_FI_DEV_XID_ERRORS[5m])
```

指标名以 exporter 版本为准，用 `{__name__=~"DCGM.*"}` 探索。

## 告警规则示例

```yaml
groups:
  - name: gpu
    rules:
      - alert: GPUTempHigh
        expr: DCGM_FI_DEV_GPU_TEMP > 85
        for: 5m
        labels:
          severity: warning

      - alert: GPUXIDError
        expr: rate(DCGM_FI_DEV_XID_ERRORS[5m]) > 0
        labels:
          severity: critical
```

## ServiceMonitor（K8s）

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dcgm-exporter
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  endpoints:
    - port: metrics
      interval: 15s
```

下一篇专讲 dcgm-exporter 部署细节。
