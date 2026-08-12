---
title: DCGM MIG 模式监控入门
date: 2026-08-23 11:45:00
tags:
  - DCGM
  - MIG
categories:
  - DCGM 新手入门
---

**MIG**（Multi-Instance GPU）将单卡切分为多实例，DCGM 支持实例级监控。

## MIG 概念

```
物理 GPU 0
  ├── GPU Instance 0（1g.5gb）
  ├── GPU Instance 1（2g.10gb）
  └── GPU Instance 2（3g.20gb）
        └── Compute Instance ...
```

## 查看 MIG 状态

```bash
nvidia-smi -L
nvidia-smi mig -lgi   # GPU Instance 列表
nvidia-smi mig -lci   # Compute Instance 列表

dcgmi discovery -l   # 显示 MIG 设备
```

## DCGM 监控 MIG

MIG 模式下，DCGM entity 可以是：
- 整卡（GPU）
- GPU Instance（GI）
- Compute Instance（CI）

```bash
# 监控特定 GPU Instance
dcgmi dmon -i 0 -e 252,150,151 -d 1
# -i 指定 entity ID（MIG 实例）
```

## dcgm-exporter 与 MIG

exporter 默认导出物理 GPU 和 MIG 实例指标，标签区分：

```
DCGM_FI_DEV_GPU_UTIL{gpu="0", GPU_I_ID="1", GPU_I_PROFILE="1g.5gb"}
```

Grafana 按 `GPU_I_ID` 分面板。

## K8s MIG 调度

```yaml
resources:
  limits:
    nvidia.com/mig-1g.5gb: 1
```

dcgm-exporter DaemonSet 需能访问 MIG 设备（与 GPU Operator MIG 策略一致）。

## 注意

| 项 | 说明 |
|----|------|
| 驱动 | MIG 需 Ampere+（A100/A30 等） |
| 切换 | MIG 模式需重置 GPU |
| 监控粒度 | 实例级显存独立，互不影响 |
| Profiling | 部分 profiling 字段 MIG 受限 |

## 常见问题

| 问题 | 解决 |
|------|------|
| 看不到 MIG 指标 | 确认 MIG 已 enable |
| 指标重复 | 区分 gpu vs GPU_I_ID 标签 |

MIG 适合**推理多租户**，监控需到实例级才算完整。
