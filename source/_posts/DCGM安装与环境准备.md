---
title: DCGM 安装与环境准备
date: 2026-08-23 09:15:00
tags:
  - DCGM
  - 安装
categories:
  - DCGM 新手入门
---

DCGM 依赖 NVIDIA 驱动，安装前需确认 GPU 与驱动版本兼容。

## 前置条件

| 项 | 要求 |
|----|------|
| GPU | Tesla / A 系列 / H 系列 / RTX 数据中心卡 |
| 驱动 | ≥ 535（视 DCGM 版本，见官方矩阵） |
| OS | Ubuntu 20.04/22.04、RHEL 8/9 |
| CUDA | 可选，DCGM 不依赖 CUDA 运行时 |

```bash
nvidia-smi
# 确认驱动正常、GPU 可见
```

## 安装 DCGM（Ubuntu DEB）

```bash
# 添加 NVIDIA 仓库后
sudo apt-get update
sudo apt-get install -y datacenter-gpu-manager

# 或从 CUDA 仓库
sudo apt-get install -y nvidia-dcgm
```

## 启动 Host Engine

```bash
sudo systemctl enable nvidia-dcgm
sudo systemctl start nvidia-dcgm
sudo systemctl status nvidia-dcgm

# 手动前台调试
nv-hostengine
```

默认监听本地 socket，供 dcgmi 和 exporter 连接。

## 验证

```bash
dcgmi discovery -l
# 列出 GPU 数量、PCI 信息、驱动版本
```

## Docker 方式（K8s 常用）

```bash
docker run -d --gpus all --cap-add SYS_ADMIN \
  --name dcgm-exporter \
  -p 9400:9400 \
  nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04
curl localhost:9400/metrics
```

## 版本对应

- DCGM 版本与驱动版本需匹配，见 [NVIDIA DCGM Release Notes](https://docs.nvidia.com/datacenter/dcgm/latest/release-notes/index.html)
- K8s 环境 dcgm-exporter 镜像 tag 含 DCGM 版本

## 常见问题

| 问题 | 解决 |
|------|------|
| Host Engine 启动失败 | 驱动未装/版本过低 |
| 看不到 GPU | `nvidia-smi` 先修 |
| 权限不足 | root 或 docker `--gpus all` |

下一篇讲 Host Engine、Field、Group 等核心概念。
