---
title: nvidia-smi 时钟与功耗管理
date: 2026-08-24 10:45:00
tags:
  - nvidia-smi
  - 功耗
categories:
  - nvidia-smi 新手入门
---

了解时钟与功耗，可判断 GPU 是否被限频、是否跑满性能。

## 查看时钟

```bash
nvidia-smi -q -d CLOCK
```

关键字段：

| 字段 | 含义 |
|------|------|
| Graphics/SM Clock | 核心时钟 MHz |
| Memory Clock | 显存时钟 |
| Max Clock | 理论最高 |
| Applications Clocks | 应用目标时钟 |

```bash
nvidia-smi --query-gpu=clocks.current.sm,clocks.max.sm,clocks.current.memory \
  --format=csv
```

## 性能状态 Perf

```
Perf: P0  最高性能
      P8  空闲省电
```

空闲时 P8 正常；**负载下仍 P8/P12** → 异常。

## 限频原因

```bash
nvidia-smi -q -d PERFORMANCE
# Clocks Throttle Reasons
```

| 原因 | 含义 |
|------|------|
| Idle | 空闲 |
| Applications Clocks Setting | 应用限制 |
| SW Power Cap | 软件功耗上限 |
| HW Slowdown | 硬件保护（温度/功耗） |
| Sync Boost | 多 GPU 同步 boost |
| Thermal Slowdown | 过热降频 |

## 功耗

```bash
nvidia-smi --query-gpu=power.draw,power.limit,power.default_limit \
  --format=csv

nvidia-smi -pl 300    # 设置功耗上限 300W（需 root，部分卡支持）
```

## Persistence Mode

```bash
nvidia-smi -pm 1      # 开启持久化，减少启动延迟
nvidia-smi -pm 0      # 关闭
```

生产训练节点建议 `-pm 1`。

## 应用时钟（管理员）

```bash
nvidia-smi -ac 1215,1410    # 内存,SM 时钟（示例，型号相关）
nvidia-smi -rac             # 重置
```

误设可能导致不稳定，需在维护窗口操作。

## 巡检关注

- 负载下 SM Clock 接近 Max
- Power 接近 Limit 且 Throttle → 正常满载
- Thermal Slowdown → 查散热
