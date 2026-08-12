---
title: nvidia-smi 多 GPU 管理入门
date: 2026-08-24 12:15:00
tags:
  - nvidia-smi
  - 多GPU
categories:
  - nvidia-smi 新手入门
---

单机多卡是训练常态，nvidia-smi 提供按卡操作的能力。

## 列出所有 GPU

```bash
nvidia-smi -L
# GPU 0: NVIDIA A100 (UUID: GPU-xxx)
# GPU 1: NVIDIA A100 (UUID: GPU-yyy)
```

## 指定 GPU

```bash
nvidia-smi -i 0
nvidia-smi -i 0,2,3
nvidia-smi -i 0 -q -d MEMORY
```

## 环境变量指定程序用卡

```bash
CUDA_VISIBLE_DEVICES=0 python train.py           # 只用 GPU 0
CUDA_VISIBLE_DEVICES=0,1 python train.py       # 用 0 和 1
CUDA_VISIBLE_DEVICES=1,0 python train.py       # 逻辑顺序，物理 1 为 cuda:0
CUDA_VISIBLE_DEVICES="" python cpu.py          # 禁用 GPU
```

## 设置 GPU 模式

```bash
# 计算模式
nvidia-smi -i 0 -c 0    # Default，多进程共享
nvidia-smi -i 0 -c 3    # Exclusive Process，单进程独占

nvidia-smi -q -d COMPUTE | grep "Compute Mode"
```

## 逐卡重置

```bash
sudo nvidia-smi --gpu-reset -i 1    # 重置 GPU 1，中断其上所有任务
```

## 逐卡功耗上限

```bash
sudo nvidia-smi -i 0 -pl 250
sudo nvidia-smi -i 0 -pl 400    # 恢复默认上限
```

## 多卡巡检脚本

```bash
for i in $(nvidia-smi --query-gpu=index --format=csv,noheader); do
  echo "=== GPU $i ==="
  nvidia-smi -i $i --query-gpu=temperature.gpu,utilization.gpu,memory.used --format=csv,noheader
done
```

## 与训练框架

| 框架 | 指定 GPU |
|------|----------|
| PyTorch | CUDA_VISIBLE_DEVICES |
| TensorFlow | tf.config.set_visible_devices |
| NCCL | 自动用可见 GPU |

多卡管理核心：**smi 看物理卡，CUDA_VISIBLE_DEVICES 映射给程序**。
