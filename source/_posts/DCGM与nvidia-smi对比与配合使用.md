---
title: DCGM 与 nvidia-smi 对比与配合使用
date: 2026-08-23 10:15:00
tags:
  - DCGM
  - nvidia-smi
categories:
  - DCGM 新手入门
---

nvidia-smi 和 DCGM 不是替代关系，而是**互补**。

## 功能对比

| 功能 | nvidia-smi | DCGM |
|------|------------|------|
| 即时快照 | ✅ 强 | ✅ dcgmi dmon |
| 持续监控 | ❌ 需脚本 | ✅ Host Engine |
| 历史存储 | ❌ | ✅ + Prometheus |
| 健康检查 | 基础 ECC | ✅ 完整体系 |
| 策略/隔离 | ❌ | ✅ Policy |
| Profiling | ❌ | ✅ DCP |
| 进程级统计 | ✅ pmon | ✅ Stats API |
| K8s 生态 | ❌ | ✅ dcgm-exporter |

## 命令对照

```bash
# 列出 GPU
nvidia-smi -L
dcgmi discovery -l

# 监控利用率
nvidia-smi dmon -s pucvmet
dcgmi dmon -e 252,203,150,151 -d 1

# 进程
nvidia-smi pmon -c 1
dcgmi stats --gpuid 0 --pid <pid>

# 拓扑
nvidia-smi topo -m
dcgmi topo
```

## 何时用 nvidia-smi

- 开发机快速看一眼
- 查驱动/CUDA 版本
- 设置 Persistence Mode
- MIG 切分（`nvidia-smi -mig ...`）

## 何时用 DCGM

- 生产 GPU 集群监控
- 告警与历史趋势
- 健康巡检自动化
- K8s + Prometheus/Grafana
- 多节点统一采集

## 配合工作流

```
开发调试：nvidia-smi
         ↓
单机验证：dcgmi discovery / dmon
         ↓
生产部署：dcgm-exporter → Prometheus
         ↓
故障排查：dcgmi health + nvidia-smi -q -x
```

## 指标名称差异

Prometheus 中 dcgm-exporter 指标如：

```
DCGM_FI_DEV_GPU_UTIL → DCGM_FI_DEV_GPU_UTIL{gpu="0"}
```

与 `nvidia_smi_utilization_gpu`（第三方 exporter）命名不同，Dashboard 勿混用。

**建议：开发用 smi，生产用 DCGM**。
