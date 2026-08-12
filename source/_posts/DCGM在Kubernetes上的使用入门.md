---
title: DCGM 在 Kubernetes 上的使用入门
date: 2026-08-23 12:30:00
tags:
  - DCGM
  - Kubernetes
categories:
  - DCGM 新手入门
---

K8s GPU 集群中，DCGM 通常由 **GPU Operator** 统一部署。

## 组件关系

```
GPU Operator
  ├── NVIDIA Driver（DaemonSet）
  ├── NVIDIA Device Plugin
  ├── dcgm-exporter（DaemonSet）
  ├── GPU Feature Discovery
  └── DCGM Host Engine（可内置 exporter）
```

## 安装 GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  -n gpu-operator --create-namespace \
  --set dcgmExporter.enabled=true \
  --set dcgm.enabled=true
```

## 验证

```bash
kubectl get pods -n gpu-operator
kubectl get nodes -o json | jq '.items[].status.capacity | select(."nvidia.com/gpu")'

# metrics
kubectl get svc -n gpu-operator | grep dcgm
```

## ServiceMonitor

GPU Operator 可自动创建 ServiceMonitor（需已装 Prometheus Operator）：

```yaml
# values.yaml
dcgmExporter:
  serviceMonitor:
    enabled: true
    interval: 15s
```

## 节点标签

```bash
kubectl label node gpu-node-1 nvidia.com/gpu.present=true
# GPU Feature Discovery 自动打标算力、MIG 等
kubectl get node gpu-node-1 -o yaml | grep nvidia.com
```

## 监控 Pod GPU 使用

1. dcgm-exporter：节点 GPU 指标
2. `kubectl top pod`：需 metrics-server（CPU/内存，非 GPU）
3. 第三方 **dcgm-telemetry** 或平台侧聚合

## 调度与监控联动

```yaml
# 节点 GPU 故障时
kubectl cordon gpu-node-1
kubectl drain gpu-node-1 --ignore-daemonsets
```

告警来自 DCGM XID/Health → Alertmanager → Runbook。

## Checklist

- [ ] GPU Operator 版本与 K8s 兼容
- [ ] dcgm-exporter 每 GPU 节点运行
- [ ] ServiceMonitor 已 scrape
- [ ] Grafana Dashboard 12239 等（NVIDIA 社区）

K8s + DCGM 是**智算平台监控的标准答案**。
