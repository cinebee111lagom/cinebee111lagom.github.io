---
title: Volcano Queue 队列与多租户资源管理
date: 2026-08-12 16:30:00
tags:
  - Volcano
  - Queue
categories:
  - Volcano
---

**Queue** 是 Volcano 的多租户资源隔离单元，类似 Slurm 的 Partition，控制「谁可以用多少 GPU/CPU」。

## Queue 定义

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: ai-team
spec:
  weight: 1
  capability:
    cpu: "64"
    memory: 128Gi
    nvidia.com/gpu: "8"
  reclaimable: true
```

| 字段 | 含义 |
|------|------|
| `capability` | 队列资源上限 |
| `deserved` | 保证份额（公平调度用） |
| `weight` | 超出 deserved 后的权重 |
| `reclaimable` | 是否可被其他队列回收空闲资源 |

## 与 Job 关联

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: pytorch-train
spec:
  queue: ai-team
  minAvailable: 4
  tasks:
    - replicas: 4
      name: worker
      template: { ... }
```

Job 提交到指定 Queue，调度器只在该 Queue 的 capability 范围内分配资源。

## 典型多租户划分

| Queue | 团队 | GPU 配额 |
|-------|------|----------|
| `prod-inference` | 在线推理 | 16 |
| `research-train` | 算法研发 | 32 |
| `batch-video` | 视频转码 | 8 |

## 公平调度（DRF）

Volcano 支持 Dominant Resource Fairness：多资源维度（CPU、内存、GPU）下尽量公平。研发队列突发训练时不会长期饿死转码小任务——取决于 weight 与 reclaimable 配置。

## 运维建议

- 定期审计 Queue capability 与实际节点容量
- 监控各 Queue 的 `allocated` / `pending` Job 数
- 新团队 onboarding 先建 Queue，再开放 RBAC

Queue 是集群资源治理的「闸门」，Gang Scheduling 解决「同时启动」，Queue 解决「谁先用」。
