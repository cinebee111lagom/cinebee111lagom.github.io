---
title: nvidia-smi 查询 GPU 详细信息
date: 2026-08-24 09:45:00
tags:
  - nvidia-smi
  - 查询
categories:
  - nvidia-smi 新手入门
---

`-q`（query）模式可查看 GPU 完整属性，排查问题时必备。

## 完整查询

```bash
nvidia-smi -q
nvidia-smi -q -i 0          # 指定 GPU 0
nvidia-smi -q -d MEMORY     # 只看 Memory 段
```

## 常用 -d 域

| 域 | 内容 |
|----|------|
| MEMORY | 显存总量、已用、BAR1 |
| UTILIZATION | GPU/Memory 利用率 |
| ECC | ECC 错误统计 |
| POWER | 功耗、限频 |
| CLOCK | SM/内存时钟 |
| COMPUTE | 计算模式 |
| PERFORMANCE | 性能状态、限频原因 |
| PCIE | PCIe 链路宽度、重传 |
| DRIVER | 驱动版本 |

```bash
nvidia-smi -q -d ECC,POWER,CLOCK
```

## --query 精确字段（推荐脚本用）

```bash
nvidia-smi --query-gpu=index,name,driver_version,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw \
  --format=csv

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
```

## 查询进程

```bash
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory \
  --format=csv
```

## XML 输出（程序解析）

```bash
nvidia-smi -q -x
nvidia-smi --query-gpu=name --format=xml
```

## 实用组合

```bash
# 所有卡型号与显存
nvidia-smi --query-gpu=index,name,memory.total --format=csv

# 温度与功耗一览
nvidia-smi --query-gpu=index,temperature.gpu,power.draw,clocks.current.sm \
  --format=csv,noheader,nounits
```

## 与默认表对比

| 方式 | 场景 |
|------|------|
| 无参数 | 人眼快速看 |
| -q | 深度排查 |
| --query | 脚本/监控采集 |

`--query` + `csv` 是写巡检脚本的**最佳入口**。
