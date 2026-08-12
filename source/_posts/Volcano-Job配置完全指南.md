---
title: Volcano Job 配置完全指南
date: 2026-08-12 17:00:00
tags:
  - Volcano
  - Job
categories:
  - Volcano
---

**Volcano Job** 是用户提交批任务的主要 CRD，封装了副本、依赖、重试与生命周期策略。

## 最小示例

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: mpi-job
spec:
  schedulerName: volcano
  minAvailable: 2
  queue: default
  tasks:
    - replicas: 1
      name: mpimaster
      policies:
        - event: TaskCompleted
          action: CompleteJob
      template:
        spec:
          containers:
            - name: mpi
              image: mpi:latest
              command: ["mpirun", "..." ]
    - replicas: 2
      name: mpiworker
      template:
        spec:
          containers:
            - name: mpi
              image: mpi:latest
```

## 关键字段

| 字段 | 说明 |
|------|------|
| `minAvailable` | Gang 最小就绪 Pod 数 |
| `tasks` | 任务组，每组独立 replicas |
| `policies` | 事件驱动动作（CompleteJob、RestartJob） |
| `plugins` | svc、env、pytorch 等插件 |
| `maxRetry` | Job 级最大重试次数 |
| `ttlSecondsAfterFinished` | 完成后自动清理 |

## PyTorch 分布式插件

Volcano 提供 `pytorch` 插件，自动注入 `MASTER_ADDR`、`WORLD_SIZE` 等：

```yaml
spec:
  plugins:
    pytorch: ["--master=mpimaster", "--worker=mpiworker", "--port=23456"]
  tasks:
    - replicas: 1
      name: master
      ...
    - replicas: 3
      name: worker
      ...
```

省去手写环境变量的麻烦。

## 生命周期策略

```yaml
policies:
  - event: PodEvicted
    action: RestartJob
  - event: TaskCompleted
    action: CompleteJob
  - event: PodFailed
    action: RestartTask
```

根据 Pod 被驱逐、任务完成、失败等事件触发不同动作。

## 与 Deployment 的区别

| | Deployment | Volcano Job |
|---|------------|-------------|
| 生命周期 | 长期运行 | 跑完即终 |
| 调度 | 逐个 Pod | Gang + Queue |
| 适用 | 微服务 | 训练、批处理 |

掌握 Job YAML 是日常使用 Volcano 的基本功。
