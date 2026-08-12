---
title: vGPU 与虚拟化场景下的 GPU 调度
date: 2026-08-12 13:00:00
tags:
  - GPU调度
  - vGPU
  - 虚拟化
categories:
  - GPU调度
---

在虚拟桌面、云游戏、多租户 GPU 云里，**vGPU** 把物理 GPU 抽象成多个虚拟 GPU 分配给不同虚拟机，调度发生在 Hypervisor 层。

## 技术栈

NVIDIA 虚拟 GPU 方案：

- **vGPU**：时间片或固定 profile（如 `NVIDIA A10-4Q`）
- **vComputeServer**：面向计算 VM
- **GRID / RTX vWS**：图形与云桌面

调度由 **NVIDIA vGPU Manager** 在宿主机完成，对 Guest 呈现为标准 GPU。

## Profile 与 QoS

每个 vGPU profile 定义：

-  framebuffer（显存上限）
-  最大显示器数 / 编解码会话数
-  时间片权重（共享物理 GPU 时）

云游戏调度示例：高付费用户绑定更高权重 profile，保证 60fps；免费用户降级 profile 或排队。

## 与容器调度的关系

K8s 裸金属 GPU 调度与 VM vGPU 调度可共存于同一数据中心：

- **训练集群**：裸金属 + MIG
- **VDI / 云游戏**：虚拟化 + vGPU
- **边缘推理**：整卡或轻量容器

统一资源池需要上层 **容量管理平台** 做跨池调度，避免 vGPU 池空闲而裸金属池排队。

## 视频场景

- **云剪辑**：每 VM 一路 NVENC，profile 限制最大会话
- **远程渲染**：vGPU 图形时间片影响帧率稳定性
- **直播推流 VM**：需预留编码引擎配额，不能仅看 SM 利用率

vGPU 调度牺牲部分裸金属性能，换来 **强租户隔离与 VM 级 SLA**——金融、政企客户常见需求。
