---
title: 多 GPU 并行调度与 NCCL 通信
date: 2026-08-12 12:30:00
tags:
  - GPU调度
  - NCCL
  - 分布式
categories:
  - GPU调度
---

单卡算力有限时，训练与大规模推理依赖**多 GPU 并行**。除「把任务放哪张卡」外，还要调度 **卡间通信**——这往往比计算本身更棘手。

## 并行范式

| 范式 | 切分维度 | 通信模式 |
|------|----------|----------|
| 数据并行 | Batch | AllReduce 梯度 |
| 张量并行 | 层内矩阵 | AllReduce / AllGather |
| 流水线并行 | 层间 | P2P 激活传递 |
| 序列并行 | 序列长度 | 分片 Attention |

现代大模型常 **3D 并行** 组合使用，调度器需同时感知拓扑与带宽。

## NCCL 的角色

**NCCL（NVIDIA Collective Communications Library）** 在 GPU 间实现高效集合通信，自动选择：

- NVLink（同节点多卡，带宽 数百 GB/s）
- PCIe（较慢，易成瓶颈）
- InfiniBand / RoCE（跨节点）

```python
# PyTorch DDP 底层依赖 NCCL
torch.distributed.init_process_group(backend="nccl")
```

调度 implication：应把通信密集的阶段安排在 **NVLink 全互联** 的节点内，跨节点只做必要同步。

## 拓扑感知调度

K8s 调度可结合节点 label：

```yaml
nodeAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
    nodeSelectorTerms:
      - matchExpressions:
          - key: gpu-topology
            operator: In
            values: ["nvlink-8"]
```

Slurm 的 `--gres=gpu:8` 配合 `CUDA_VISIBLE_DEVICES` 与拓扑检测脚本，是 HPC 侧常见做法。

## 视频分布式推理

多卡视频超分、实时拼接场景：

- 按 **时间片** 或 **空间块** 分卡
- 边界帧需要 halo exchange，通信量小于训练但仍需调度
- 尾卡等待会导致帧率抖动——需静态分片 + 负载均衡

多 GPU 调度 = **计算放置 + 通信编排**，NCCL 是其中关键一环。
