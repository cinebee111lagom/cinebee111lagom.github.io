---
title: nvidia-smi 新手入门：什么是 nvidia-smi 与适用场景
date: 2026-08-24 09:00:00
tags:
  - nvidia-smi
  - GPU
  - 入门
categories:
  - nvidia-smi 新手入门
---

**nvidia-smi**（NVIDIA System Management Interface）是 NVIDIA 官方 GPU 管理命令行工具，随驱动安装，是 GPU 运维的「第一站」。

## nvidia-smi 能做什么

| 能力 | 说明 |
|------|------|
| 查看 GPU | 型号、数量、驱动/CUDA 版本 |
| 监控 | 利用率、显存、温度、功耗 |
| 进程 | 谁在用哪张卡、占多少显存 |
| 拓扑 | GPU 间 NVLink/PCIe 连接 |
| 配置 | 持久化模式、功耗上限、MIG 切分 |
| 诊断 | ECC 错误、XID、降频原因 |

## 适用场景

**适合**：
- 开发机快速看 GPU 状态
- 训练/推理节点人工巡检
- 排查「显存满了」「GPU 不可见」
- 学习 GPU 基础概念

**不够用时**：
- 集群长期监控 → 用 **DCGM + Prometheus**
- 历史趋势与告警 → dcgm-exporter
- 深度性能分析 → Nsight

## 与 DCGM 关系

```
nvidia-smi：快照、单机、即时查询（轻量）
DCGM：持续监控、策略、Prometheus（生产）
```

二者互补，见本系列第 18 篇。

## 基本用法

```bash
nvidia-smi
```

一条命令即可看到 GPU 列表、利用率、显存、进程。

## 学习路线

```
基础输出 → 查询参数 → 监控命令 → 拓扑/MIG → Docker/K8s → 巡检脚本
```

本系列 20 篇带你从零掌握 nvidia-smi 日常运维所需技能。
