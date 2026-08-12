---
title: DCGM Profiling 性能分析入门
date: 2026-08-23 10:45:00
tags:
  - DCGM
  - Profiling
categories:
  - DCGM 新手入门
---

DCGM Profiling 模块（DCP）提供硬件级性能计数器，比利用率更细粒度。

## 启用 Profiling

```bash
# 查看 profiling 模块
dcgmi modules --list

# 启动 profiling 字段监控
dcgmi dmon -e 1002,1003,1004,1005 -d 1
# 示例 field：DRAM 活跃、SM 活跃、Pipe 活跃等（版本而异）
```

具体 Field ID 查阅当前版本文档：`dcgmi profile --help`

## 关键 Profiling 指标

| 指标 | 含义 |
|------|------|
| SM Active | SM 真正执行指令的时间比 |
| SM Occupancy | Warp 占用率 |
| DRAM Active | 显存带宽活跃比 |
| FP64/FP32/FP16 Active | 各精度管道利用率 |
| Tensor Active | Tensor Core 利用率（训练关键） |

## 解读示例

```
GPU Util 100% 但 Tensor Active 低
  → 可能 memory bound 或非 Tensor 算子

GPU Util 50% 但 Tensor Active 高
  → 可能 batch 小或 kernel launch 开销

DRAM Active 持续 90%+
  → 内存带宽瓶颈，考虑算子融合/数据类型
```

## dcgm-exporter Profiling 指标

dcgm-exporter 可开启 profiling 指标导出（配置 `--collectors` 或环境变量，视版本）：

```yaml
environment:
  - DCGM_EXPORTER_COLLECTORS=/etc/dcgm-exporter/dcp-metrics-included.csv
```

## 与 Nsight 关系

| 工具 | 粒度 | 场景 |
|------|------|------|
| DCGM Profiling | 节点级、持续 | 集群监控 |
| Nsight Systems | 时间线 trace | 单 job 深度分析 |
| Nsight Compute | Kernel 级 | 算子优化 |

DCGM Profiling 适合**长期趋势**，Nsight 适合**单次调优**。

## 注意

- Profiling 有轻微开销，生产可采样开启
- 需较新驱动与 DCGM 版本
- A100/H100 支持字段与 V100 不同

Profiling 帮你回答「GPU 到底在算什么」而不只是「忙不忙」。
