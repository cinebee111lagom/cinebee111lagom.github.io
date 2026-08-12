---
title: nvidia-smi 安装与 NVIDIA 驱动基础
date: 2026-08-24 09:15:00
tags:
  - nvidia-smi
  - 驱动
categories:
  - nvidia-smi 新手入门
---

`nvidia-smi` 随 **NVIDIA 驱动** 安装，没有独立安装包。

## 驱动与 smi 关系

```
NVIDIA Driver（内核模块 + 用户态库）
  ├── nvidia-smi（/usr/bin/nvidia-smi）
  ├── libnvidia-ml.so（NVML 库）
  └── nvidia-modprobe 等
```

## 检查是否已安装

```bash
which nvidia-smi
nvidia-smi
```

正常输出 GPU 表格即表示驱动可用。

## Linux 安装驱动（Ubuntu 示例）

```bash
# 推荐：官方 runfile 或 apt
sudo apt update
sudo apt install -y nvidia-driver-535

# 或 CUDA 仓库
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-drivers
```

安装后**重启**，再执行 `nvidia-smi`。

## 版本信息解读

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.154.05   Driver Version: 535.154.05   CUDA Version: 12.2  |
+-----------------------------------------------------------------------------+
```

| 字段 | 含义 |
|------|------|
| NVIDIA-SMI | smi 工具版本 |
| Driver Version | 驱动版本（关键） |
| CUDA Version | 驱动支持的**最高** CUDA 运行时版本 |

## 内核模块

```bash
lsmod | grep nvidia
nvidia-smi -q | grep "Driver Version"
```

模块未加载 → 驱动安装失败或 Secure Boot 阻止。

## Windows

安装 [GeForce/Quadro 驱动](https://www.nvidia.com/drivers) 后，PowerShell 中同样可用 `nvidia-smi`（需 PATH 含 NVIDIA 目录）。

## 常见问题

| 问题 | 解决 |
|------|------|
| command not found | 驱动未装或 PATH 无 |
| No devices found | 无 GPU / 虚拟机未透传 / 驱动不匹配 |
| NVML: Driver/library version mismatch | 驱动升级后未重启 |

驱动是 GPU 可用性的**前提**，smi 只是其接口。
