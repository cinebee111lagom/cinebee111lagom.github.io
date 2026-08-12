---
title: GPU 计算节点部署架构选型指南
date: 2026-08-25 09:15:00
tags:
  - nvidia-smi
  - SRE
  - GPU
categories:
  - nvidia-smi SRE
---

生产 GPU 环境常见四种形态，选型决定后续 nvidia-smi 巡检粒度与故障域。

## 架构对比

| 形态 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| 裸金属 | 大规模训练 | 性能最优、无虚拟化损耗 | 运维重、交付慢 |
| VM + GPU 直通 | 混合云 | 隔离好、弹性 | 调度复杂、性能略损 |
| K8s + Device Plugin | 推理/训练混部 | 统一调度、弹性 | 驱动/运行时依赖链长 |
| 云托管 GPU | 快速起步 | 免运维节点 | 成本高、可观测受限 |

## 节点规格维度

| 维度 | 决策点 |
|------|--------|
| GPU 型号 | A100/H100/L40S/T4，训练 vs 推理 |
| 单机卡数 | 4/8 卡，影响 NVLink 拓扑 |
| CPU/内存 | 通常 1:1 ~ 2:1 CPU 核 per GPU |
| 网络 | IB/RoCE 用于多机训练 |
| 存储 | 本地 NVMe vs 共享并行文件系统 |

## 验证命令（上线前）

```bash
nvidia-smi -L
nvidia-smi topo -m
nvidia-smi --query-gpu=name,memory.total,pcie.link.gen.current --format=csv
```

## 推荐路径

```
POC 单机 → 裸金属池（训练）+ K8s GPU 池（推理）
         → 统一 DCGM 监控 + smi 巡检脚本
```

## 反模式

- 训练与推理混在同一节点且无 cgroup/ MIG 隔离
- 不同驱动版本节点进同一调度池
- 无拓扑文档，NUMA 错配导致 PCIe 瓶颈

选型文档应包含：**GPU 型号、驱动版本、K8s 标签、监控 endpoint**。
