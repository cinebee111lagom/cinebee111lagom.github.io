---
title: DCGM 健康检查与诊断入门
date: 2026-08-23 10:30:00
tags:
  - DCGM
  - 健康检查
categories:
  - DCGM 新手入门
---

DCGM Health 模块持续检测 GPU 硬件与驱动健康，是 SRE 巡检核心。

## 启动健康监控

```bash
# 对所有 GPU 启用全部健康检测
dcgmi health -g 1 -s a

# 查看当前健康状态
dcgmi health -g 1 -c
```

输出示例：

```
Health Monitor Report
GPU 0 : Healthy
GPU 1 : Warning - Detected more than 8 PCIe replays
GPU 2 : Failure - XID 48 detected
```

## 健康项类型

| 类别 | 检测内容 |
|------|----------|
| PCIe | 重传、带宽降级 |
| Memory | ECC 错误、退休页 |
| NVLink | 错误计数、状态 |
| Thermal | 过热、风扇 |
| Power | 功耗异常 |
| Driver | XID、重启 |
| SM | 静默错误 |

## 响应级别

| 状态 | 含义 | 动作 |
|------|------|------|
| Healthy | 正常 | 无 |
| Warning | 潜在问题 | 关注、计划维护 |
| Failure | 严重故障 | 隔离 GPU、换卡 |

## 与 Policy 联动

Policy 模块可在健康 Failure 时自动执行动作（需配置）：

```bash
dcgmi policy --help
# 例如：XID 超阈值 → 记录日志 / 通知
```

## 巡检脚本

```bash
#!/bin/bash
dcgmi health -g 1 -c | grep -E "Warning|Failure" && exit 1
exit 0
```

接入 cron 或 K8s DaemonSet 探针。

## 常见 Warning/Failure

| 现象 | 可能原因 |
|------|----------|
| PCIe replays | 线缆、插槽、Riser |
| XID 13/31/48 | 驱动/显存/非法访问 |
| ECC 错误增多 | 显存硬件老化 |
| Thermal alert | 风道、风扇、机房温度 |

## nvidia-smi 补充

```bash
nvidia-smi -q -d PERFORMANCE,ECC,POWER,CLOCK,COMPUTE
nvidia-smi -q -x | grep -i xid
```

Health 是**自动化**，`-q` 是**人工深挖**。
