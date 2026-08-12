---
title: nvidia-smi 拓扑与 NUMA 亲和性
date: 2026-08-24 10:30:00
tags:
  - nvidia-smi
  - 拓扑
categories:
  - nvidia-smi 新手入门
---

多卡训练性能受 GPU 间连接影响，拓扑矩阵告诉你「卡与卡怎么连」。

## 拓扑矩阵

```bash
nvidia-smi topo -m
```

示例输出：

```
        GPU0    GPU1    GPU2    GPU3    CPU Affinity    NUMA Affinity
GPU0     X      NV2     NV2     NV2     0-15            0
GPU1    NV2      X      NV2     NV2     0-15            0
GPU2    NV2     NV2      X      NV2     16-31           1
GPU3    NV2     NV2     NV2      X      16-31           1
```

## 图例

| 标记 | 含义 | 带宽 |
|------|------|------|
| NV# | NVLink # 链路 | 最高 |
| PIX | 同一 PCIe 交换机 | 中 |
| PXB | 跨 PCIe 桥 | 中低 |
| SYS | 跨 CPU/UPI | 最低 |
| X | 自身 | — |

## NUMA 亲和

```bash
nvidia-smi topo -m
# CPU Affinity：GPU 离哪些 CPU 核近
# NUMA Affinity：NUMA 节点
```

**最佳实践**：GPU 绑 NUMA 就近 CPU，减少跨节点内存访问。

```bash
numactl --cpunodebind=0 --membind=0 python train.py
```

## 生成拓扑图（部分版本）

```bash
nvidia-smi topo -p    # 打印拓扑图
```

## 与 NCCL 关系

NCCL 自动选通信路径，但拓扑差（全 SYS）时 AllReduce 慢。

排查训练通信慢：

1. `nvidia-smi topo -m`
2. 设置 `NCCL_DEBUG=INFO`
3. 考虑 NVLink 线缆/模块

## dcgmi topo

```bash
dcgmi topo    # DCGM 版，与 smi 类似
```

拓扑是**多卡性能优化**的第一步，训练框架调优前先看。
