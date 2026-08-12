---
title: GPU 节点在 Kubernetes 上的 SRE 部署
date: 2026-08-25 11:15:00
tags:
  - nvidia-smi
  - SRE
  - Kubernetes
categories:
  - nvidia-smi SRE
---

K8s GPU 节点的 SRE 链路：**驱动 → container toolkit → Device Plugin → 调度 → 监控**。

## 组件清单

| 组件 | 作用 |
|------|------|
| NVIDIA Driver | 宿主机 GPU |
| nvidia-container-toolkit | 容器内 GPU |
| NVIDIA Device Plugin / GPU Operator | K8s 资源 `nvidia.com/gpu` |
| dcgm-exporter DaemonSet | 监控 |
| Node Feature Discovery | 标签 GPU 型号 |

## 节点验收

```bash
# 宿主机
nvidia-smi -L

# 节点标签
kubectl get node <node> -o json | jq '.status.allocatable["nvidia.com/gpu"]'

# 测试 Pod
kubectl run gpu-test --rm -it --restart=Never \
  --limits=nvidia.com/gpu=1 \
  --image=nvcr.io/nvidia/cuda:12.2.0-base-ubuntu22.04 -- nvidia-smi
```

Pod 内 smi 输出应与宿主机一致（驱动版本、卡数可见 subset）。

## 运维 Runbook 要点

| 操作 | 步骤 |
|------|------|
| 驱动升级 | cordon → drain → 升级 → smi 验收 → uncordon |
| GPU 故障 | 标记 `gpu-unhealthy=true`，禁止调度 |
| 显存泄漏 Pod | delete pod，宿主机 smi 确认释放 |

## 调度与隔离

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
nodeSelector:
  nvidia.com/gpu.product: NVIDIA-A100-SXM4-40GB
```

MIG 场景使用 `nvidia.com/mig-1g.5gb` 等资源名（取决于 Device Plugin 配置）。

## 常见问题

| 问题 | 排查 |
|------|------|
| Pod Pending | describe pod，Device Plugin 日志 |
| smi 在容器内失败 | runtimeClass、nvidia runtime 配置 |
| 可见卡数错误 | `NVIDIA_VISIBLE_DEVICES` 环境变量 |

## 反模式

- Device Plugin 与驱动版本不兼容未测就全量推
- 无 GPU 节点专用 taint，CPU 作业占 GPU 节点
- 仅监控 Pod 不监控宿主机 smi/ECC

K8s GPU 节点 SLO：**测试 Pod smi 成功 + allocatable GPU 数正确** 作为上线门禁。
