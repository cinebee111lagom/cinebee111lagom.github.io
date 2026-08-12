---
title: GPU 集群作业调度：Slurm 与 Volcano
date: 2026-08-12 13:30:00
tags:
  - GPU调度
  - Slurm
  - Volcano
categories:
  - GPU调度
---

单机 GPU 调度之上，是**集群级作业调度**：谁先拿卡、拿几张、能否抢占。HPC 与 AI 平台各有成熟方案。

## Slurm（HPC 传统）

```bash
sbatch --gres=gpu:4 --partition=ai train.sh
```

Slurm 特性：

- **Partition** 队列：开发 / 生产 / 紧急
- **Fair-share**：历史用量影响优先级
- **Gang Scheduling**：`--nodes=2 --ntasks-per-node=4` 全齐才启动
- 与 **MPI + NCCL** 深度集成

适合超算中心、固定团队共享集群。

## Volcano（云原生 AI）

Volcano 为 K8s 设计，核心 CRD：

- **Queue**：资源配额与优先级
- **PodGroup**：组调度语义
- **Job**：批任务生命周期

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
spec:
  minAvailable: 4
  tasks:
    - replicas: 4
      template:
        spec:
          containers:
            - resources:
                limits:
                  nvidia.com/gpu: 1
```

适合弹性伸缩、与 CI/CD 集成的 MLOps 流程。

## 调度策略对比

| 能力 | Slurm | Volcano |
|------|-------|---------|
| 生态 | HPC 成熟 | K8s 原生 |
| 弹性 | 弱 | 强 |
| 抢占 | 支持 | 支持 |
| 队列公平 | Fair-share | Queue + Priority |
| 视频批处理 | 批脚本 | CronJob + Queue |

## 视频批转码队列设计

建议：

1. 短视频（<5min）与高优先级 Job 进 **express queue**
2. 4K 长片进 **batch queue**，夜间低价时段跑
3. 设置 **GPU 利用率回填**：小任务塞进空闲 Slot

集群调度器是 GPU 资源的「交通警察」——规则清晰，才能避免大 Job 饿死小 Job，或测试任务占卡不还。
