---
title: nvidia-smi 监控 GPU 利用率与显存
date: 2026-08-24 10:00:00
tags:
  - nvidia-smi
  - 监控
categories:
  - nvidia-smi 新手入门
---

持续观察利用率与显存，是判断 GPU 「忙不忙」「够不够」的基本功。

## 单次查看

```bash
nvidia-smi --query-gpu=index,utilization.gpu,utilization.memory,memory.used,memory.free,memory.total \
  --format=csv
```

## 循环刷新

```bash
nvidia-smi -l 1              # 每 1 秒刷新整表
nvidia-smi -lms 500          # 每 500 毫秒
watch -n 1 nvidia-smi        # 配合 watch 命令
```

## dmon 动态监控

```bash
# 监控功耗、利用率、显存等
nvidia-smi dmon -s pucvmet -d 1 -c 10
# -s: 监控项  -d: 间隔秒  -c: 次数
```

dmon 监控项字母：

| 字母 | 含义 |
|------|------|
| p | 功耗 |
| u | SM 利用率 |
| c | 计算/util |
| v | 显存 |
| m | 内存控制器 |
| e | ECC 错误 |
| t | 温度 |

```bash
nvidia-smi dmon -s u -d 1    # 只看利用率
```

## 利用率解读

| GPU-Util | 含义 |
|----------|------|
| 0~10% | 空闲或等 I/O |
| 50~80% | 中等负载，可能有数据瓶颈 |
| 90~100% | 计算密集 |

Memory-Util 高而 GPU-Util 低 → **内存带宽瓶颈**。

## 显存监控

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits | \
  awk -F', ' '{printf "GPU: %d/%d MiB (%.0f%%)\n", $1, $2, $1/$2*100}'
```

显存持续接近 100% → 需减 batch 或换大显存卡。

## 简单日志记录

```bash
while true; do
  date '+%Y-%m-%d %H:%M:%S'
  nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
  sleep 5
done >> gpu.log
```

长期监控建议改用 **DCGM + Prometheus**，见 DCGM 入门系列。
