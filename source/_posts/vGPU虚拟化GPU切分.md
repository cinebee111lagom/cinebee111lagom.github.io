---
title: vGPU：虚拟化环境下的 GPU 切分
date: 2026-08-13 10:00:00
tags:
  - GPU切分
  - vGPU
categories:
  - GPU切分
---

**vGPU** 在 Hypervisor 层将物理 GPU 虚拟化，分配给多个虚拟机，适合 VDI、云桌面、云游戏。

## 与 MIG 的区别

| | MIG | vGPU |
|---|-----|------|
| 层级 | GPU 硬件 | Hypervisor |
| 租户 | 容器 / 裸金属 | 虚拟机 |
| 隔离 | 硬件 | 虚拟化 + 时间片 |
| 典型场景 | K8s 推理 | 云桌面、远程渲染 |

## vGPU Profile

NVIDIA 预定义 profile，如 `A10-2Q`（2GB 显存）、`A10-4Q`（4GB）：

- **Q 系列**：图形 / 桌面
- **C 系列**：计算
- **B 系列**：混合

每个 VM 绑定一个 profile，Hypervisor 调度物理 GPU 时间片。

## 时间片 QoS

共享物理 GPU 时，vGPU Manager 按 profile 权重分配：

- 高权重 profile 获得更多 GPU 时间
- 低权重在 burst 时被限流

云游戏场景：付费用户高 QoS，免费用户低 QoS。

## 容器场景的替代

K8s 裸金属集群通常**不用 vGPU**，而用 MIG 或整卡 + Device Plugin。vGPU 更适合 VM 池或 OpenStack 环境。

## 部署要点

- 宿主机安装 vGPU Manager 驱动
- Guest VM 安装对应 Grid 驱动
- License Server（部分 profile 需要）

vGPU 切分是**虚拟化栈**的 GPU 共享，与 MIG 互补而非替代。
