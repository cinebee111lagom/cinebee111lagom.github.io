---
title: GPU 故障演练与混沌工程
date: 2026-08-25 12:45:00
tags:
  - nvidia-smi
  - SRE
  - 混沌工程
categories:
  - nvidia-smi SRE
---

GPU 故障代价高（长训中断），定期演练验证 **发现、隔离、恢复** 链路。

## 演练目标

| 能力 | 验证点 |
|------|--------|
| 监控 | XID/掉卡/ECC 告警是否触发 |
| 调度 | 故障节点是否自动 cordon |
| 作业 | checkpoint 恢复 / 重调度 |
| 值班 | Runbook 是否可执行 |

## 安全演练场景

| 场景 | 方法 | 环境 |
|------|------|------|
| smi 不可用 | 停 dcgm-exporter / 模拟驱动 hang | staging |
| 单卡高温 | 限风道或 stress（谨慎） | staging |
| 节点 drain | kubectl drain GPU 节点 | staging/prod 低峰 |
| 进程泄漏 | 故意留 zombie CUDA 进程 | staging |

**禁止**在生产无审批注入真实 XID 或物理损坏。

## 演练脚本示例（staging）

```bash
#!/bin/bash
# 模拟 GPU 检查失败告警
HOST=$(hostname)
if nvidia-smi &>/dev/null; then
  echo "Pre-check OK: $(nvidia-smi --query-gpu=count --format=csv,noheader | head -1) GPUs"
fi
# 由混沌平台 cordon 并验证告警
kubectl cordon "$HOST"
sleep 300
kubectl uncordon "$HOST"
nvidia-smi -L
```

## 成功标准

- P0 告警 ≤ 5 分钟送达
- 值班按 Runbook 完成 cordon
- 作业 RTO 符合 SLA
- 演练报告归档

## 频率

- **季度**：掉卡/节点 drain 演练
- **半年**：全链路（监控 + 调度 + 平台）
- **驱动升级前**：staging 故障回归

## 反模式

- 只演练监控不响应急救
- 生产首次 failover 发生在真实故障
- 演练不更新 Runbook

演练结论应反馈到 **告警阈值** 与 **Device Plugin 行为** 优化。
