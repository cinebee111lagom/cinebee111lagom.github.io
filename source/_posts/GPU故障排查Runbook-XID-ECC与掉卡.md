---
title: GPU 故障排查 Runbook：XID、ECC 与掉卡
date: 2026-08-25 11:45:00
tags:
  - nvidia-smi
  - SRE
  - 故障
categories:
  - nvidia-smi SRE
---

GPU 硬件/驱动故障通常表现为 **XID 日志、ECC 错误、nvidia-smi 不可见**，Runbook 需标准化。

## 第一步：现场快照

```bash
nvidia-smi
nvidia-smi -q
nvidia-smi -L
dmesg | tail -50
dmesg | grep -i xid
```

保存输出到工单，便于 RMA 与厂商支持。

## XID 错误

| 步骤 | 动作 |
|------|------|
| 1 | `dmesg \| grep -i Xid` 记录完整行 |
| 2 | 查 [NVIDIA XID 文档](https://docs.nvidia.com/deploy/xid-errors/index.html) 对应含义 |
| 3 | 若作业可迁移：cordon 节点，重启作业 |
| 4 | 重复 XID：重启节点 → 仍复现则换卡/RMA |

常见 XID 13/31/43/79 等与驱动、ECC、双位错误相关，**同一卡 24h 内 2 次同类 XID → 下线**。

## ECC 错误

```bash
nvidia-smi --query-gpu=index,ecc.mode.current,\
ecc.errors.corrected.aggregate.total,\
ecc.errors.uncorrected.aggregate.total \
  --format=csv
```

| 类型 | 动作 |
|------|------|
| Corrected 缓慢增长 | 监控，计划维护窗口 |
| Uncorrected > 0 | **立即下线**，数据风险 |
| Pending | 等待 row remapping 结果 |

## 掉卡 / smi 失败

```bash
lspci | grep -i nvidia
lsmod | grep nvidia
sudo nvidia-smi -r   # GPU reset（若支持且无作业）
sudo systemctl restart nvidia-persistenced
# 最后手段：reboot
```

仍不可见 → 硬件/PCIe 故障，走 RMA。

## 决策树（简）

```
nvidia-smi 失败？
  ├─ lspci 无 GPU → 硬件/PCIe
  ├─ lspci 有、smi 无 → 驱动 reload / reboot
  └─ smi 有 XID/ECC → 按上表下线
```

## 反模式

- 忽略 corrected ECC 直到 uncorrected
- 未 cordon 继续调度新作业到故障节点
- XID 日志未接入 centralized logging

每次 GPU 硬件事件应更新 **节点健康档案**（序列号、故障次数、RMA 记录）。
