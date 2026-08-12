---
title: DCGM GPU 监控指标解读
date: 2026-08-23 10:00:00
tags:
  - DCGM
  - 监控
  - GPU
categories:
  - DCGM 新手入门
---

读懂 DCGM 指标，才能正确判断 GPU 是「忙」还是「出问题」。

## 利用率类

| 指标 | 含义 | 正常参考 |
|------|------|----------|
| GPU Util | SM 活跃百分比 | 训练 80~100%，推理视 batch |
| Memory Copy Util | H2D/D2H 拷贝占用 | 数据预处理高 |
| Encoder/Decoder Util | 视频编解码 | 多媒体任务 |

**注意**：GPU Util 低不等于空闲——可能在等 DataLoader 或 NCCL。

## 显存类

| 指标 | 含义 |
|------|------|
| FB Used / Free | Framebuffer 已用/空闲 |
| BAR1 Used | BAR1 映射内存 |

OOM 前 FB Used 接近总量；泄漏时 Used 持续涨不释放。

## 温度与功耗

| 指标 | 告警参考 |
|------|----------|
| GPU Temp | > 83°C 降频，> 90°C 危险 |
| Power Usage | 接近 TDP 上限正常 |
| Power Violation | 功耗触顶计数 |

## 时钟

| 指标 | 说明 |
|------|------|
| SM Clock | 核心频率，降频=thermal/power throttle |
| Memory Clock | 显存频率 |
| Throttle Reasons | 限频原因位掩码 |

```bash
dcgmi dmon -e 100,101,112 -d 1
# SM 时钟、内存时钟、限频原因
```

## NVLink / PCIe

| 指标 | 场景 |
|------|------|
| NVLink Bandwidth | 多卡 AllReduce |
| PCIe Replay Counter | 链路错误 |
| NVLink CRC Errors | 线缆/连接器问题 |

## XID 错误

```
DCGM_FI_DEV_XID_ERRORS
```

XID 是驱动/硬件错误码，任何增长都需排查（显存 ECC、GPU 掉卡等）。

## 综合判断

```
训练慢？
  → GPU Util 低 + Mem Copy 高 → 数据瓶颈
  → GPU Util 高 + Power 低 → 可能 CPU 调度
  → Temp 高 + Clock 低 → 散热问题
  → XID 增 → 硬件/驱动故障
```

下一篇对比 nvidia-smi，说明何时用哪个工具。
