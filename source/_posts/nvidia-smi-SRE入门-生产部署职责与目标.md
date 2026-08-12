---
title: nvidia-smi SRE 入门：生产部署职责与目标
date: 2026-08-25 09:00:00
tags:
  - nvidia-smi
  - SRE
  - GPU
categories:
  - nvidia-smi SRE
---

GPU 计算节点是 AI 训练与推理的物理底座。SRE 的目标是让它在**可用性、利用率、稳定性**之间长期可运维——**nvidia-smi** 是现场诊断与巡检的第一工具，生产监控则与 DCGM/Prometheus 配合。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | 驱动版本、容器运行时、K8s Device Plugin |
| 基线 | 持久化模式、功耗上限、ECC、MIG 策略 |
| 容量 | 显存、算力、PCIe/NVLink 带宽、节点 GPU 密度 |
| 可观测 | smi 巡检、dcgm-exporter、XID/ECC 告警 |
| 进程治理 | 僵尸进程、显存泄漏、多租户隔离 |
| 变更 | 驱动升级、固件、MIG 重切、节点下线 |
| 安全 | 物理访问、SSH、容器 GPU 隔离 |
| 容灾 | 多 AZ 池化、故障节点摘除、作业重调度 |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| GPU 节点可用率 | 99.5% ~ 99.9%（按池） |
| 单卡故障发现时间 | ≤ 5 分钟（监控） |
| 掉卡/不可见恢复 RTO | ≤ 30 分钟（重启/换节点） |
| 训练作业因 GPU 故障中断率 | < 0.1%/月 |
| 驱动版本漂移 | 0（同一池统一版本） |

## 工具分工

```
nvidia-smi：值班现场、Runbook 第一步、脚本巡检、变更前后验证
DCGM + Prometheus：7×24 指标、告警、Grafana
Fabric Manager / MIG：A100/H100 多实例切分运维
```

## 架构演进路径

```
单机开发机 → 裸金属 GPU 池 → K8s + GPU Operator
          → MIG 细粒度切分 → 多集群联邦调度
          → 云 GPU（EKS/GKE/ACK）+ 统一监控
```

## 与平台、算法团队的边界

- **算法/训练**：作业配置、CUDA 版本、显存需求
- **平台/K8s**：调度、配额、Device Plugin、镜像
- **GPU SRE**：驱动、节点基线、监控告警、故障 Runbook、容量

本系列 20 篇覆盖 GPU 节点从架构、驱动、监控、告警到演练的完整 SRE 路径。
