---
title: Volcano 与 Kubernetes 默认调度器对比
date: 2026-08-12 18:30:00
tags:
  - Volcano
  - Kubernetes
categories:
  - Volcano
---

何时用 Volcano，何时用默认 kube-scheduler？一张表说清楚。

## 能力对比

| 能力 | kube-scheduler | Volcano |
|------|----------------|---------|
| 单 Pod 调度 | ✅ | ✅ |
| Gang Scheduling | ❌ | ✅ |
| Queue / 配额 | ❌ | ✅ |
| 批 Job CRD | ❌ | ✅ |
| 优先级抢占 | 基础 | 增强 |
| PyTorch/MPI 插件 | ❌ | ✅ |
| 长期服务 | ✅ 最佳 | 不适用 |

## 调度语义

**默认调度器**：贪心、逐个、无组约束。适合 Deployment、StatefulSet。

**Volcano**：组约束、队列公平、批生命周期。适合 Job、训练、Spark。

## 共存部署

```yaml
# 微服务 — 默认
spec:
  schedulerName: default-scheduler

# 训练 Job — Volcano
spec:
  schedulerName: volcano
```

同一集群、同一节点池，按 workload 类型分流。

## 与其他方案

| 方案 | 特点 |
|------|------|
| **Kueue** | K8s 官方队列，轻量，Gang 支持演进中 |
| **Slurm on K8s** | 传统 HPC 语义 |
| **YuniKorn** | 另一批调度器，Apache 项目 |
| **Volcano** | CNCF，GPU/AI 生态成熟 |

选型建议：已深度用 K8s + GPU 训练 → **Volcano**；纯 HPC → Slurm；轻量队列 → Kueue。

## 迁移路径

1. 安装 Volcano，默认 workload 不变
2. 新训练 Job 指定 `schedulerName: volcano`
3. 配置 Queue 划分团队
4. 逐步将批任务从裸 Pod / Deployment 迁到 Volcano Job

不是替换 K8s，而是**补全批调度拼图**。
