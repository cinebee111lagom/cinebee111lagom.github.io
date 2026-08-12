---
title: DCGM 实战：GPU 集群监控搭建
date: 2026-08-23 13:15:00
tags:
  - DCGM
  - 实战
categories:
  - DCGM 新手入门
---

从零搭建一个 4 节点 GPU 集群的 DCGM 监控栈。

## 目标架构

```
4× GPU Node（dcgm-exporter:9400）
        ↓
Prometheus（scrape 15s）
        ↓
Grafana Dashboard + Alertmanager
```

## 步骤 1：节点准备

```bash
# 每 GPU 节点
nvidia-smi
sudo apt install datacenter-gpu-manager
sudo systemctl enable --now nvidia-dcgm

docker run -d --name dcgm-exporter --gpus all --cap-add SYS_ADMIN \
  --restart unless-stopped -p 9400:9400 \
  nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04
```

## 步骤 2：Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: dcgm
    static_configs:
      - targets:
          - gpu1:9400
          - gpu2:9400
          - gpu3:9400
          - gpu4:9400
```

## 步骤 3：告警规则

```yaml
# gpu-alerts.yml
groups:
  - name: gpu
    rules:
      - alert: HighGPUTemperature
        expr: DCGM_FI_DEV_GPU_TEMP > 85
        for: 5m
      - alert: GPUHighMemory
        expr: DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95
        for: 10m
      - alert: GPUXID
        expr: increase(DCGM_FI_DEV_XID_ERRORS[5m]) > 0
```

## 步骤 4：Grafana

- Import Dashboard 12239
- 配置 Prometheus 数据源
- 添加告警通知渠道

## 步骤 5：巡检脚本

```bash
#!/bin/bash
for node in gpu{1..4}; do
  echo "=== $node ==="
  ssh $node "dcgmi health -g 1 -c | grep -v Healthy || true"
done
```

cron 每日 8:00 执行。

## 验证清单

- [ ] 4 节点 metrics 均有数据
- [ ] 人工跑训练 job，Util 上升
- [ ] 模拟告警（调低阈值测试）
- [ ] 文档化 Runbook

## 扩展

- 上 K8s：换 GPU Operator DaemonSet
- 多租户：按 Namespace 标签扩展
- 对接训练平台 API

这个实战覆盖 **90% 智算平台 GPU 监控需求**。
