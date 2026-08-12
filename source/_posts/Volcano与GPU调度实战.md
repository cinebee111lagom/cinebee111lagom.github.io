---
title: Volcano 与 GPU 调度实战
date: 2026-08-12 17:30:00
tags:
  - Volcano
  - GPU调度
categories:
  - Volcano
---

Volcano 本身不管理 GPU 驱动，但与 **NVIDIA Device Plugin** 配合，可高效调度整卡训练 Job。

## 资源声明

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
  requests:
    nvidia.com/gpu: 1
```

Volcano 调度器读取节点 `nvidia.com/gpu` 的 allocatable，在 Gang 语义下同时分配多张卡。

## 8 卡 DDP 训练示例

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: ddp-resnet
spec:
  schedulerName: volcano
  minAvailable: 8
  queue: gpu-train
  plugins:
    pytorch: ["--master=master", "--worker=worker", "--port=23456"]
  tasks:
    - replicas: 1
      name: master
      template:
        spec:
          containers:
            - name: train
              image: pytorch:2.2-cuda12.1
              resources:
                limits:
                  nvidia.com/gpu: 1
    - replicas: 7
      name: worker
      template:
        spec:
          containers:
            - name: train
              image: pytorch:2.2-cuda12.1
              resources:
                limits:
                  nvidia.com/gpu: 1
```

`minAvailable: 8` 保证 8 张 GPU 同时就绪，避免 DDP 初始化 hang。

## 与 MIG 的配合

若节点启用 MIG，Device Plugin 暴露 `nvidia.com/mig-1g.10gb` 等资源。Volcano Queue capability 需对应 MIG 规格：

```yaml
capability:
  nvidia.com/mig-1g.10gb: "16"
```

Gang 语义不变，只是资源名从整卡变为 MIG 实例。

## 常见问题

| 现象 | 排查 |
|------|------|
| Job 长期 Pending | 集群 GPU 不足 minAvailable；Queue capability 满 |
| 部分 Pod Running 部分 Pending | schedulerName 未设为 volcano |
| OOM | 非调度问题，检查单卡显存与 batch size |

## 监控

结合 DCGM Exporter 与 Volcano 指标：

- `volcano_queue_allocated_gpu`
- Job phase（Pending / Running / Completed）
- PodGroup unschedulable 原因

Volcano + GPU = 云原生分布式训练的标准组合之一。
