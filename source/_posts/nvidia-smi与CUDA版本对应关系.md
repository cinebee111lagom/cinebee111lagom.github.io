---
title: nvidia-smi 与 CUDA 版本对应关系
date: 2026-08-24 12:00:00
tags:
  - nvidia-smi
  - CUDA
categories:
  - nvidia-smi 新手入门
---

新手常混淆 smi 显示的 CUDA Version 与本地安装的 CUDA Toolkit。

## smi 中的 CUDA Version

```
| NVIDIA-SMI 535.154.05   Driver Version: 535.154.05   CUDA Version: 12.2  |
```

此 **CUDA Version** 表示：当前驱动支持的**最高 CUDA 运行时 API 版本**，不是已安装的 CUDA 路径。

## 三者关系

```
Driver Version  →  决定支持的 CUDA 上限
CUDA Toolkit    →  nvcc 编译器版本（可 ≤ 驱动支持上限）
Application     →  运行时需要 Driver 足够新
```

## 查看已安装 CUDA Toolkit

```bash
nvcc --version
cat /usr/local/cuda/version.txt   # 若存在
ls /usr/local/ | grep cuda
```

## 兼容性原则

| 规则 | 说明 |
|------|------|
| 驱动 ≥ 应用要求 | 低驱动跑不了高 CUDA 程序 |
| Toolkit 可低于 smi 显示 | 用 CUDA 11.8 编译，驱动支持 12.x 可运行 |
| 向前兼容 | 新驱动跑旧 CUDA 程序通常可以 |

查表：[CUDA Toolkit Release Notes](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/) 中的 Driver 对应表。

## 实例

```
Driver 535 → CUDA Version 12.2（smi 显示）
安装 CUDA 12.1 Toolkit → nvcc 12.1 → OK
运行 cu12.2 编译的程序 → OK
运行 cu12.4 编译的程序 → 可能需升级驱动
```

## 容器环境

```bash
docker run --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
# 容器内 smi 显示宿主机驱动信息
```

容器 CUDA 版本需 ≤ 宿主机驱动支持上限。

## 排查 CUDA 错误

```
CUDA driver version is insufficient for CUDA runtime version
```

→ 升级驱动，或降低程序 CUDA 版本。

smi 的 CUDA Version 是**兼容性上限速查**，不是安装版本号。
