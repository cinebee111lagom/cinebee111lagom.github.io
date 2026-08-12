---
title: DCGM 多 GPU 与 NVLink 监控入门
date: 2026-08-23 11:30:00
tags:
  - DCGM
  - NVLink
  - 多GPU
categories:
  - DCGM 新手入门
---

多卡训练依赖 NVLink/PCIe 通信，DCGM 可监控互联健康与带宽。

## 拓扑查看

```bash
dcgmi topo
nvidia-smi topo -m
```

输出 GPU 间连接类型：NV#（NVLink）、PIX（PCIe 切换）、SYS（跨 CPU）。

## NVLink 指标

| Field | 含义 |
|-------|------|
| NVLink Bandwidth | 各链路带宽 |
| NVLink Errors | CRC/恢复错误 |
| NVLink State | 链路 up/down |

```bash
dcgmi dmon -e 409,410,411 -d 1
# field ID 因版本而异，用 dmon --list 确认
```

Prometheus：

```promql
DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL
rate(DCGM_FI_DEV_NVLINK_REPLAY_ERROR_COUNT_TOTAL[5m])
```

## 多卡训练场景

```
8×GPU AllReduce
  → NVLink 全互联：带宽最优
  → PCIe only：通信成瓶颈，GPU Util 可能假高
```

## PCIe 监控

```bash
# PCIe 重传（健康检查也会报）
dcgmi health -g 1 -c | grep -i pcie
```

PCIe replay 持续增长 → 硬件问题，非软件调优能解决。

## Group 批量监控

```bash
dcgmi group -c all-gpus -a 0,1,2,3,4,5,6,7
dcgmi dmon -g 2 -e 252,203 -d 5
```

## 告警建议

| 告警 | 条件 |
|------|------|
| NVLink Down | 链路状态异常 |
| NVLink Errors | rate > 0 |
| PCIe Replay | 持续 Warning |

## 排障

1. `dcgmi topo` 确认物理连接
2. 对比 NVLink 带宽与理论峰值
3. 训练框架 NCCL 日志（`NCCL_DEBUG=INFO`）
4. 线缆/模块重新插拔（数据中心运维）

多卡性能问题，**先看互联，再看算力**。
