---
title: nvidia-smi 常见问题与排查
date: 2026-08-24 13:00:00
tags:
  - nvidia-smi
  - 排查
categories:
  - nvidia-smi 新手入门
---

nvidia-smi 相关故障的快速排查手册。

## 命令无法执行

| 错误 | 解决 |
|------|------|
| command not found | 安装驱动，检查 PATH |
| Failed to initialize NVML | 驱动未加载/损坏，重启或重装 |
| Driver/library version mismatch | 驱动升级后未重启 |

```bash
sudo modprobe nvidia
sudo reboot
```

## 看不到 GPU

```bash
lspci | grep -i nvidia
nvidia-smi
dmesg | grep -i nvidia
```

| 原因 | 场景 |
|------|------|
| 虚拟机未透传 | 云主机需 GPU 实例 |
| 驱动不对 | 重装匹配版本 |
| 硬件故障 | lspci 都没有 → 硬件 |
| Secure Boot | 禁用或签名驱动 |

## 显存未释放

```bash
nvidia-smi --query-compute-apps=pid --format=csv,noheader
kill <pid>
# 仍占用
sudo fuser -v /dev/nvidia*
sudo nvidia-smi --gpu-reset -i 0
```

## GPU 利用率异常

| 现象 | 排查 |
|------|------|
| 0% 有进程 | DataLoader/IO 瓶颈 |
| 100% loss 不降 | 学习率/代码 bug，非 smi 问题 |
| 低 Perf 状态 | -q -d PERFORMANCE 看 throttle |

## 温度过高

```bash
nvidia-smi --query-gpu=temperature.gpu,fan.speed --format=csv
nvidia-smi -q -d PERFORMANCE | grep -i thermal
```

> 83°C 常见降频阈值，查机房散热/风道。

## XID / ECC

见本系列 ECC 篇：`dmesg | grep -i xid`

## Docker/K8s

```bash
# Docker
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# K8s
kubectl get pods -A | grep device-plugin
```

## 排查顺序

```
1. nvidia-smi 能否运行？
2. GPU 是否可见（-L）？
3. 进程/显存（默认输出）？
4. 温度/ECC/XID（-q）？
5. 拓扑/驱动版本？
6. 容器/K8s 层？
```

逐层下钻，避免一上来就 reboot。
