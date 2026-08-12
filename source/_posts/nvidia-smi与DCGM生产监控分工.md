---
title: nvidia-smi 与 DCGM 生产监控分工
date: 2026-08-25 13:15:00
tags:
  - nvidia-smi
  - SRE
  - DCGM
categories:
  - nvidia-smi SRE
---

生产环境应明确 **smi vs DCGM** 边界，避免重复建设或监控盲区。

## 能力对比

| 维度 | nvidia-smi | DCGM |
|------|------------|------|
| 部署 | 随驱动 | 独立 Host Engine + exporter |
| 数据 | 快照/短周期脚本 | 持续字段采样 |
| 告警 | 需自建 | 内置 Policy + exporter |
| 进程级 | 基础 | 更细 Profiling |
| 多节点 | 需 Ansible/cron | Prometheus 原生 |
| 学习成本 | 低 | 中 |

## 推荐分工

```
┌─────────────────────────────────────────┐
│  DCGM：7×24 指标、Grafana、P0/P1 告警   │
├─────────────────────────────────────────┤
│  nvidia-smi：值班 SSH、Runbook、变更验收  │
├─────────────────────────────────────────┤
│  dmesg/XID：日志采集 + 告警规则           │
└─────────────────────────────────────────┘
```

## 典型工作流

| 事件 | 工具 |
|------|------|
| 告警：GPU 高温 | Grafana → ssh `nvidia-smi` 确认 |
| 驱动升级后 | smi 快照对比 + DCGM metric 恢复 |
| 租户报 OOM | smi 查进程 → DCGM 看历史显存曲线 |
| 容量评审 | Prometheus 聚合 + smi  spot check |

## 统一字段映射

| smi query 字段 | DCGM FI 字段（示例） |
|----------------|----------------------|
| utilization.gpu | DCGM_FI_DEV_GPU_UTIL |
| memory.used | DCGM_FI_DEV_FB_USED |
| temperature.gpu | DCGM_FI_DEV_GPU_TEMP |
| power.draw | DCGM_FI_DEV_POWER_USAGE |

文档化映射，避免 Dashboard 两套口径。

## 反模式

- 只用 smi cron 冒充生产监控
- DCGM 已部署仍要求值班只认 smi
- 二者告警重复、路由不同造成混乱

**原则**：DCGM 管「趋势与告警」，smi 管「人与变更」。
