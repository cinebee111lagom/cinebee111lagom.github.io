---
title: DCGM 新手入门：什么是 DCGM 与适用场景
date: 2026-08-23 09:00:00
tags:
  - DCGM
  - GPU
  - 入门
categories:
  - DCGM 新手入门
---

**DCGM**（Data Center GPU Manager）是 NVIDIA 官方的数据中心 GPU **管理与监控**工具集，面向运维、SRE 和 AI 平台工程师。

## DCGM 能做什么

| 能力 | 说明 |
|------|------|
| 监控 | 温度、功耗、利用率、显存、NVLink |
| 健康检查 | GPU 硬件故障、XID 错误、降级检测 |
| 策略 | 功耗/温度阈值、隔离异常 GPU |
| Profiling | 算力/内存带宽、Tensor Core 利用率 |
| 集成 | Prometheus、K8s Device Plugin 生态 |

## 与 nvidia-smi 对比

| | nvidia-smi | DCGM |
|---|------------|------|
| 定位 | 单机快照查询 | 持续监控 + 策略 |
| 多机 | 需自行汇总 | Host Engine 统一采集 |
| 指标导出 | 有限 | 原生 Prometheus 支持 |
| 健康诊断 | 基础 | 完整 Health Check 体系 |
| K8s | 无官方集成 | dcgm-exporter 标准方案 |

```
训练/推理节点 → DCGM Host Engine → dcgm-exporter → Prometheus → Grafana
```

## 适用场景

**适合**：
- GPU 集群（训练、推理、HPC）
- K8s GPU 节点监控
- GPU SRE / 智算平台运维
- 需要历史指标与告警

**不适合**：
- 单卡桌面开发机（nvidia-smi 够用）
- 非 NVIDIA GPU（AMD 用 ROCm 生态）

## 组件概览

| 组件 | 作用 |
|------|------|
| **nv-hostengine** | 后台守护进程，采集 GPU 数据 |
| **dcgmi** | 命令行管理工具 |
| **dcgm-exporter** | Prometheus 指标导出 |
| **libdcgm** | C/Python API |

## 学习路线

```
概念 → 安装 → dcgmi 命令 → 指标解读 → exporter + Grafana → K8s → 排查
```

本系列 20 篇从零带你掌握 DCGM 日常使用与 GPU 监控入门。
