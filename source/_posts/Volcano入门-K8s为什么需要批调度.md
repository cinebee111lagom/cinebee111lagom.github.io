---
title: Volcano 入门：Kubernetes 为什么需要批调度
date: 2026-08-12 15:00:00
tags:
  - Volcano
  - Kubernetes
categories:
  - Volcano
---

**Volcano** 是 CNCF 下的 Kubernetes 原生批调度系统，专为 AI 训练、大数据、HPC 等**批量计算**场景设计。当默认调度器搞不定时，Volcano 登场。

## 默认调度器的局限

Kubernetes 默认调度器（kube-scheduler）为**长生命周期服务**优化：

- 逐个 Pod 调度，无「组」概念
- 不理解 Gang Scheduling（全有或全无）
- 缺少队列、公平份额、作业优先级等批处理语义

分布式训练典型场景：1 个 Parameter Server + 8 个 Worker，**8 个 Worker 必须同时就绪**才能开始。默认调度器可能先调度 5 个，其余 3 个 Pending——集群有卡却跑不起来。

## Volcano 解决什么

| 能力 | 说明 |
|------|------|
| Gang Scheduling | PodGroup 内 minAvailable 全部就绪才调度 |
| Queue | 多租户队列与资源配额 |
| 优先级 / 抢占 | 高优先级 Job 可抢占低优先级 |
| 批处理 Job CRD | Volcano Job 封装 Replica、重试、生命周期 |
| GPU 感知 | 与 Device Plugin 配合，支持 GPU 整卡调度 |

## 适用场景

- 深度学习分布式训练（PyTorch DDP、Horovod）
- Spark / Flink on K8s
- 基因测序、渲染农场等批处理
- 多团队共享 GPU 集群

## 与 Slurm 的关系

Slurm 是 HPC 老牌调度器；Volcano 是 **K8s 生态内的批调度层**。云原生团队往往选 Volcano + K8s，传统超算中心仍用 Slurm。二者可共存于同一数据中心不同集群。

下一篇介绍 Volcano 的架构与核心组件。
