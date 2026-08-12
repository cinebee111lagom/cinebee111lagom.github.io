---
title: DCGM 核心概念：Host Engine、Field、Group
date: 2026-08-23 09:30:00
tags:
  - DCGM
  - 概念
categories:
  - DCGM 新手入门
---

理解 DCGM 架构模型，是正确使用 dcgmi 和 exporter 的基础。

## 架构

```
dcgmi / dcgm-exporter / 自定义程序
           ↓ libdcgm API
      nv-hostengine（Host Engine）
           ↓ NVML
      NVIDIA Driver → GPU 硬件
```

**Host Engine** 是中心守护进程，所有客户端通过它访问 GPU。

## Field（字段/指标）

DCGM 用 **Field ID** 表示监控项，例如：

| Field | 含义 |
|-------|------|
| `DCGM_FI_DEV_GPU_TEMP` | GPU 温度 |
| `DCGM_FI_DEV_POWER_USAGE` | 功耗（W） |
| `DCGM_FI_DEV_GPU_UTIL` | GPU 利用率 |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | 内存带宽利用率 |
| `DCGM_FI_DEV_FB_USED` | 显存已用 |
| `DCGM_FI_DEV_XID_ERRORS` | XID 错误计数 |

Field 分为：
- **Watch**：周期性采样（监控用）
- **Entity**：GPU / GPU Instance（MIG）/ Compute Instance

## Group（组）

将多块 GPU 逻辑分组，便于批量操作：

```bash
# 创建组
dcgmi group -c gpu-group-1 -a 0,1,2,3

# 对组做 health check
dcgmi health -g 1 -s a
```

| 组类型 | 说明 |
|--------|------|
| Manual | 手动指定 GPU ID |
| All | 所有 GPU |
| Empty | 空组，后续添加 |

## Entity Group（实体组）

MIG 模式下，entity 可以是 GPU Instance 或 Compute Instance。

## Job（作业统计）

DCGM 可跟踪**进程级** GPU 使用（Stats），用于计费或排查：

```bash
dcgmi stats --gpuid 0 --job 12345
```

## 模块（Modules）

| 模块 | 功能 |
|------|------|
| Core | 基础监控 |
| Policy | 策略与响应 |
| Health | 健康检查 |
| Profiling | 性能计数器 |
| Config | 配置管理 |

```bash
dcgmi modules --list
```

掌握 Field + Group + Host Engine 三角，后续命令行和 exporter 配置都会更清晰。
