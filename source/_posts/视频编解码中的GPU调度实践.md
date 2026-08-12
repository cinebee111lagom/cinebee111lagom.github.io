---
title: 视频编解码中的 GPU 调度实践
date: 2026-08-12 12:00:00
tags:
  - GPU调度
  - 视频
categories:
  - GPU调度
---

视频业务是 GPU 调度的高频场景：解码、滤镜、缩放、编码全在卡上完成。调度设计直接决定**路数、延迟与电费**。

## 硬件编解码单元

NVIDIA GPU 除 CUDA Core 外，还有专用 **NVDEC / NVENC** 引擎。它们与 SM 独立，可并行工作：

```
CPU 读盘 → NVDEC 解码 → CUDA Kernel 处理 → NVENC 编码 → 输出
```

调度要点是让 NVDEC、SM、NVENC **流水线重叠**，而非串行等待。

## 多路转码调度模型

典型转码服务架构：

1. **任务队列**（Redis / Kafka）接收转码 Job
2. **Worker** 从队列拉任务，绑定 GPU 设备
3. 每 GPU 维护 **Slot 池**（如 MIG 实例或固定路数）

```python
# 概念示意：每卡最多 concurrent_slots 路
with gpu_slot.acquire(gpu_id):
    pipeline.run(input_path, output_path)
```

Slot 数量由压测得出：1080p H.265 → NVENC 约 5–8 路/卡（视代际与 preset 而定）。

## 帧级 vs 任务级调度

| 粒度 | 说明 | 适用 |
|------|------|------|
| 任务级 | 一路视频占一个 Slot 直到结束 | 点播转码 |
| 帧级 | 多路帧交错进同一 Pipeline | 超低延迟直播 |

帧级调度复杂度高，需无锁环形缓冲与精细的 Stream 同步，但可把 NVENC 利用率推到 90%+。

## 与 CPU 的协同

并非所有滤镜都适合 GPU。轻量 OSD、元数据解析留 CPU；重滤镜（AI 超分、降噪）上 GPU。调度器应避免 **CPU 等 GPU、GPU 等 CPU** 的互相阻塞——用异步回调和双缓冲缓解。

## 监控指标

- 每路 **FPS / 实际倍速**
- NVENC/NVDEC **利用率**（非 SM 利用率）
- **PCIe 带宽**（4K RAW 上卡是隐形瓶颈）
- 队列 **等待时间**（调度是否饥饿）

视频场景是检验 GPU 调度成色的试金石：算力、专用引擎、IO 三者必须协同。
