---
title: nvidia-smi MIG 模式入门
date: 2026-08-24 11:15:00
tags:
  - nvidia-smi
  - MIG
categories:
  - nvidia-smi 新手入门
---

**MIG**（Multi-Instance GPU）将单卡切分为多个独立 GPU 实例，适合推理多租户。

## 支持型号

A100、A30、H100 等数据中心卡（Ampere/Hopper）。

## 查看 MIG 状态

```bash
nvidia-smi -L
# MIG 开启时显示 GPU 0 + MIG 子设备

nvidia-smi -i 0 -q | grep -i mig
# MIG Mode: Enabled / Disabled
```

## 启用 MIG（需无运行任务）

```bash
sudo nvidia-smi -i 0 -mig 1       # 启用 MIG 模式
sudo nvidia-smi -i 0 -mig 0       # 禁用（需先销毁实例）
```

## 创建 GPU Instance

```bash
# 查看可用 profile
nvidia-smi mig -lgip

# 创建 1g.5gb 实例（示例 profile ID 见输出）
sudo nvidia-smi mig -cgi 19,19,19,19,19,19,19 -C
# 或按文档指定 GPU Instance Profile

# 列出 GPU Instance
nvidia-smi mig -lgi
```

## Compute Instance

```bash
nvidia-smi mig -lcip
sudo nvidia-smi mig -cci -i 0
nvidia-smi mig -lci
```

## 销毁实例

```bash
sudo nvidia-smi mig -dci -ci 0    # 删 Compute Instance
sudo nvidia-smi mig -dgi -gi 0    # 删 GPU Instance
```

## 使用 MIG 设备

```bash
CUDA_VISIBLE_DEVICES=MIG-GPU-xxx python inference.py
# K8s: nvidia.com/mig-1g.5gb: 1
```

## 注意

| 项 | 说明 |
|----|------|
| 切换 MIG | 需停止所有 GPU 进程 |
| 显存 | 各实例隔离 |
| 训练 | 大模型训练通常不用 MIG |
| 监控 | smi 可看到 GI/CI 列 |

MIG 切分用 smi，持续监控 MIG 实例用 **DCGM**（见 DCGM 入门系列）。
