---
title: dcgm-exporter 部署实战
date: 2026-08-23 11:15:00
tags:
  - DCGM
  - dcgm-exporter
categories:
  - DCGM 新手入门
---

dcgm-exporter 是 NVIDIA 官方 Prometheus exporter，K8s GPU 节点标配。

## 裸机 systemd

```bash
# 确保 hostengine 运行
systemctl start nvidia-dcgm

# 下载 release 二进制或使用容器
/usr/local/bin/dcgm-exporter -f /etc/dcgm-exporter/default-counters.csv
```

## Docker Compose

```yaml
services:
  dcgm-exporter:
    image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    cap_add:
      - SYS_ADMIN
    ports:
      - "9400:9400"
    restart: unless-stopped
```

## K8s DaemonSet（精简）

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: gpu-operator
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
    spec:
      nodeSelector:
        nvidia.com/gpu.present: "true"
      containers:
        - name: dcgm-exporter
          image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04
          securityContext:
            capabilities:
              add: ["SYS_ADMIN"]
          ports:
            - name: metrics
              containerPort: 9400
          volumeMounts:
            - name: proc
              mountPath: /host/proc
              readOnly: true
      volumes:
        - name: proc
          hostPath:
            path: /proc
```

## 自定义采集字段

```csv
# default-counters.csv 片段
DCGM_FI_DEV_GPU_TEMP, gauge
DCGM_FI_DEV_POWER_USAGE, gauge
DCGM_FI_DEV_GPU_UTIL, gauge
DCGM_FI_DEV_FB_USED, gauge
DCGM_FI_DEV_XID_ERRORS, counter
```

```yaml
args:
  - "-f"
  - "/etc/dcgm-exporter/custom.csv"
```

## GPU Operator 集成

NVIDIA GPU Operator 可自动部署 dcgm-exporter，与 device plugin、driver 一并管理：

```bash
helm install gpu-operator nvidia/gpu-operator -n gpu-operator --create-namespace
```

## 验证

```bash
kubectl port-forward ds/dcgm-exporter 9400:9400 -n gpu-operator
curl localhost:9400/metrics | grep DCGM_FI_DEV_GPU_UTIL
```

## 常见问题

| 问题 | 解决 |
|------|------|
| 无 metrics | 驱动/MIG 配置 |
| 权限错误 | SYS_ADMIN cap |
| 指标不全 | 检查 csv 配置文件 |

exporter 部署好后，接上 Prometheus 即可做全集群 GPU 大盘。
