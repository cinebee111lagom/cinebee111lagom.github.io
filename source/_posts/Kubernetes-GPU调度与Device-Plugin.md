---
title: Kubernetes GPU 调度与 NVIDIA Device Plugin
date: 2026-08-12 10:00:00
tags:
  - GPU调度
  - Kubernetes
categories:
  - GPU调度
---

在 K8s 集群里调度 GPU，本质是让调度器「认识」GPU 这种异构资源，并在 Pod 启动时把正确的设备句柄注入容器。

## 资源模型

K8s 通过 Extended Resource 暴露 GPU：

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

节点上必须运行 **NVIDIA Device Plugin**，它负责：

1. 调用 `nvidia-smi` / NVML 枚举 GPU
2. 向 kubelet 注册 `nvidia.com/gpu` 资源容量
3. Pod 绑定时，将 `NVIDIA_VISIBLE_DEVICES` 等环境变量写入容器

## 调度流程

```
Pending Pod → kube-scheduler 过滤/打分有 GPU 的节点
           → 绑定 Node
           → kubelet 创建设备 → Device Plugin Allocate()
           → 容器内可见指定 GPU
```

默认调度器按「整卡」分配。一张 A100 即使只用了 2GB 显存，也会被标记为整卡占用——这是**粗粒度调度**的典型痛点。

## GPU Operator 的角色

NVIDIA GPU Operator 一站式部署：

- Device Plugin
- DCGM Exporter（监控）
- MIG Manager（可选）
- Container Runtime 配置（`nvidia` runtime class）

生产集群建议通过 Operator 而非手工装插件，减少驱动版本与容器运行时不匹配的风险。

## 与 Volcano / Kueue 的配合

纯 K8s 默认调度器不理解 Gang Scheduling（一组 Pod 必须同时启动）。AI 训练 Job 常用 **Volcano** 或 **Kueue**：

- 队列与配额管理
- PodGroup 语义：minAvailable 全部就绪才调度
- 抢占与回填策略

视频批处理流水线同样受益于队列化：转码任务 burst 时不会挤爆显存。

## 常见问题

| 问题 | 原因 | 方向 |
|------|------|------|
| Pod Pending | 节点无可用 GPU | 扩容或释放僵尸任务 |
| OOM | 多 Pod 共享策略不当 | MIG / 显存限额 |
| 驱动不匹配 | 镜像 CUDA 版本 ≠ 节点驱动 | 统一版本矩阵 |

K8s 层解决的是「哪张卡给谁」；卡内如何切片，需要 MIG、vGPU 或 MPS，见后续文章。
