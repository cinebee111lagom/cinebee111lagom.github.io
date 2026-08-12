---
title: nvidia-smi 与 DCGM 配合使用
date: 2026-08-24 13:15:00
tags:
  - nvidia-smi
  - DCGM
categories:
  - nvidia-smi 新手入门
---

nvidia-smi 和 DCGM 都基于 **NVML**，面向不同场景，配合使用效果最佳。

## 能力对比

| 场景 | nvidia-smi | DCGM |
|------|------------|------|
| 开发机看一眼 | ✅ | 过重 |
| SSH 登录巡检 | ✅ dmon/health | ✅ dcgmi |
| Prometheus 监控 | ❌ 需脚本 | ✅ exporter |
| 健康策略 | ❌ | ✅ |
| 历史趋势 | ❌ | ✅ |
| MIG 切分 | ✅ mig 子命令 | ✅ 实例监控 |
| Profiling | ❌ | ✅ DCP |

## 日常分工

```
开发调试     → nvidia-smi
运维巡检     → nvidia-smi + dcgmi health
生产监控     → dcgm-exporter → Prometheus
故障深挖     → smi -q + dcgmi health + dmesg XID
```

## 命令对照

```bash
# 列表
nvidia-smi -L
dcgmi discovery -l

# 监控
nvidia-smi dmon -s pucvmet
dcgmi dmon -e 155,203,252 -d 1

# 拓扑
nvidia-smi topo -m
dcgmi topo

# 进程
nvidia-smi pmon
dcgmi stats -g 1 -e

# ECC
nvidia-smi -q -d ECC
dcgmi health -g 1 -c
```

## 脚本层配合

```bash
#!/bin/bash
# 快速 smi 筛查
nvidia-smi --query-gpu=index,temperature.gpu,utilization.gpu --format=csv,noheader,nounits | \
while IFS=, read idx temp util; do
  if [ "$temp" -gt 85 ]; then
    echo "GPU $idx hot, running DCGM health..."
    dcgmi health -g 1 -c | grep -A2 "GPU $idx"
  fi
done
```

## 学习路径建议

1. 本系列掌握 smi
2. 学 **DCGM 新手入门** 系列上生产监控
3. GPU 调度系列理解业务层

**smi 是钥匙，DCGM 是监控体系**。
