---
title: DCGM 策略配置与阈值管理入门
date: 2026-08-23 12:15:00
tags:
  - DCGM
  - Policy
categories:
  - DCGM 新手入门
---

DCGM Policy 模块可在指标超阈值时触发动作，实现自动化响应。

## Policy 能力

| 能力 | 说明 |
|------|------|
| 条件 | 温度、功耗、XID、PCIe 错误等 |
| 动作 | 日志、回调脚本、隔离 GPU |
| 持久化 | 策略可保存到配置文件 |

## 查看与配置

```bash
dcgmi policy --help
dcgmi policy -g 1 -o   # 查看当前策略

# 注册回调（示例，具体参数见 man）
dcgmi policy -g 1 -r -t 85
# 温度超 85°C 触发
```

## 典型策略场景

| 场景 | 条件 | 动作 |
|------|------|------|
| 过热保护 | Temp > 90°C | 告警 + 标记节点不可调度 |
| XID 检测 | XID 新增 | 告警 + 记录 |
| 功耗封顶 | Power > TDP | 通知 |

生产环境复杂策略多通过 **Prometheus Alertmanager** 实现，DCGM Policy 适合节点本地快速响应。

## 与 K8s 联动

```bash
# Policy 触发脚本示例
#!/bin/bash
kubectl cordon $(hostname)
kubectl label node $(hostname) gpu-health=failed
```

## Config 模块

```bash
# 锁定/设置 GPU 配置（时钟、ECC 等）
dcgmi config -g 1 -e 2100,900
dcgmi config -g 1 -r   # 重置默认
```

需维护窗口操作，影响运行中任务。

## 建议

| 层级 | 工具 |
|------|------|
| 节点本地 | DCGM Policy + 脚本 |
| 集群级 | Prometheus 告警 + K8s cordon/drain |
| 工单 | Alertmanager → PagerDuty/飞书 |

新手先掌握 **Prometheus 告警**，再探索 DCGM Policy 本地回调。
