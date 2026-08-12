---
title: nvidia-smi ECC 与 XID 错误排查
date: 2026-08-24 11:00:00
tags:
  - nvidia-smi
  - ECC
  - XID
categories:
  - nvidia-smi 新手入门
---

数据中心 GPU 的 ECC 与 XID 错误是**硬件健康**的关键信号。

## ECC 错误查询

```bash
nvidia-smi -q -d ECC
```

| 字段 | 含义 |
|------|------|
| Single Bit ECC | 可纠正错误（警告） |
| Double Bit ECC | 不可纠正（严重） |
| Volatile / Aggregate | 本次启动 / 累计 |

```bash
nvidia-smi --query-gpu=ecc.errors.corrected.volatile.total,ecc.errors.uncorrected.volatile.total \
  --format=csv
```

**Double Bit 任何增长** → 考虑换卡。

## 启用/查看 ECC 模式

```bash
nvidia-smi -q | grep -i ecc
# ECC Mode: Enabled / Disabled
```

A100/H100 等默认开启；部分消费卡无 ECC。

## XID 错误

XID 是驱动记录在 `/var/log/syslog` 或 dmesg 中的 GPU 错误：

```bash
dmesg | grep -i Xid
grep -i xid /var/log/syslog
nvidia-smi -q -x | grep -i xid
```

## 常见 XID 码

| XID | 常见含义 |
|-----|----------|
| 8 | GPU 因其他 GPU 错误停止 |
| 13 | 图形异常或驱动问题 |
| 31 | GPU 内存页不可用 |
| 43 | GPU 停止响应，需 reset |
| 48 | 双位 ECC 错误 |
| 63 | 驱动/硬件不一致 |
| 79 | GPU  fallen off the bus |

完整列表见 NVIDIA XID 文档。

## 处理流程

```
1. 记录 XID 码、GPU ID、时间
2. nvidia-smi -q -d ECC 查 ECC
3. 若严重：隔离节点，不再调度新任务
4. nvidia-smi --gpu-reset -i N 或 reboot
5. 仍复现 → RMA 换卡
```

## 与 DCGM 配合

```bash
dcgmi health -g 1 -c    # 自动汇总健康项
```

smi 适合**单次查 ECC/XID**，DCGM 适合**持续监控告警**。
