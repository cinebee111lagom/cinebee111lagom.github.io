---
title: 视频转码场景的 GPU 切分实践
date: 2026-08-13 12:00:00
tags:
  - GPU切分
  - 视频
  - NVENC
categories:
  - GPU切分
---

视频转码依赖 **NVENC/NVDEC** 专用引擎，与 SM 算力独立。GPU 切分可在一卡上稳定跑多路转码。

## 单路资源消耗

| 分辨率 | 编码 | 约显存 | NVENC 会话 |
|--------|------|--------|------------|
| 1080p H.264 | 实时 | 1–2 GB | 1 |
| 4K H.265 | 实时 | 2–4 GB | 1 |
| 1080p + AI 滤镜 | CUDA | +2 GB | 1 |

A100 的 NVENC 会话数有上限（视驱动与 profile），MIG 1g 实例通常支持 1–2 会话。

## MIG 多路转码架构

```
A100 (7 × 1g.10gb)
├── MIG-0 → Worker Pod：1080p 路 1
├── MIG-1 → Worker Pod：1080p 路 2
├── ...
└── MIG-6 → Worker Pod：1080p 路 7
```

每路独立 Slot，**互不影响尾延迟**。

## Slot 池调度

```python
# 概念：每 MIG UUID 一个 slot
MIG_SLOTS = discover_mig_instances()  # 7 个

def transcode(job):
    with acquire_slot(MIG_SLOTS):
        run_ffmpeg_nvenc(job)
```

队列拉任务 → 绑定空闲 MIG 实例 → 转码完成释放。

## 与 CPU 软编对比

| | GPU 切分多路 | CPU 多进程软编 |
|---|-------------|----------------|
| 吞吐 | 高 | 低 |
| 延迟 | 稳定（MIG 隔离） | 受 CPU 核数限制 |
| 成本 | 需 GPU 节点 | 无 GPU 成本 |

## 监控

- 每 MIG 实例的 NVENC 利用率（DCGM）
- 每路实际 FPS / 倍速
- 队列等待时间

视频场景是 MIG **ROI 最高**的场景之一：路数可预测、负载均匀、隔离需求明确。
