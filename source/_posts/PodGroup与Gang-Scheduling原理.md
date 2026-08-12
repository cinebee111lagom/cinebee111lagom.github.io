---
title: PodGroup 与 Gang Scheduling 原理
date: 2026-08-12 16:00:00
tags:
  - Volcano
  - Gang-Scheduling
categories:
  - Volcano
---

**Gang Scheduling**（组调度）是 Volcano 的招牌能力：一组 Pod **要么一起启动，要么一起等待**，避免资源碎片化。

## 问题场景

8 卡分布式训练，需要 8 个 Worker 同时跑 AllReduce：

- 默认 K8s：先调度 6 个，2 个 Pending
- 6 个 Worker 启动后互相等待，**死锁或超时**
- 集群显示「有 2 张卡空闲」，但 Job 无法推进

## PodGroup 机制

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: PodGroup
metadata:
  name: train-pg
  namespace: default
spec:
  minMember: 8        # 至少 8 个 Pod 就绪才视为可调度
  queue: default
  priorityClassName: high-priority
```

Volcano Job 创建时自动关联 PodGroup。调度器在 **minMember 未满足前不会 Bind 任何一个 Pod**（或采用等价策略，确保 gang 语义）。

## minAvailable vs minMember

在 Volcano Job 中常见：

```yaml
spec:
  minAvailable: 8
  tasks:
    - replicas: 8
      name: worker
      template:
        spec:
          schedulerName: volcano
          containers:
            - resources:
                limits:
                  nvidia.com/gpu: 1
```

`minAvailable: 8` 表示 8 个 task Pod 全部可调度时才整体放行。

## 调度流程

1. 用户提交 Job → 创建 PodGroup + N 个 Pod（Pending）
2. vc-scheduler 评估：当前集群能否同时满足 N 个 Pod 的资源
3. **能** → 批量 Bind；**不能** → 全部保持 Pending，等待资源释放
4. 资源释放后，重新评估，一次性调度

## 最佳实践

- `minAvailable` 设为关键路径 Pod 数（通常等于 worker replicas）
- 避免 minAvailable 大于集群总容量（永远 Pending）
- 多 Job 竞争时，配合 Queue 与 priority 使用

Gang Scheduling 是 Volcano 区别于默认调度器的核心，分布式训练必备。
