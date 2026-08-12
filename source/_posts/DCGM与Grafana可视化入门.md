---
title: DCGM 与 Grafana 可视化入门
date: 2026-08-23 12:45:00
tags:
  - DCGM
  - Grafana
categories:
  - DCGM 新手入门
---

Grafana 将 DCGM 指标变成可读的 GPU 集群大盘。

## 数据源

Prometheus 添加 scrape dcgm-exporter 后，Grafana 选 Prometheus 数据源。

## 导入社区 Dashboard

| ID | 名称 |
|----|------|
| 12239 | NVIDIA DCGM Exporter Dashboard |
| 14017 | NVIDIA GPU Metrics（变体） |

Grafana → Dashboards → Import → 输入 ID → 选 Prometheus。

## 核心面板

| 面板 | PromQL 示例 |
|------|-------------|
| GPU 利用率 | `DCGM_FI_DEV_GPU_UTIL` |
| 显存 | `DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) * 100` |
| 温度 | `DCGM_FI_DEV_GPU_TEMP` |
| 功耗 | `DCGM_FI_DEV_POWER_USAGE` |
| 按节点 | `sum by (instance, gpu) (...)` |

## 变量（Variables）

```
Label: node
Query: label_values(DCGM_FI_DEV_GPU_UTIL, instance)

Label: gpu
Query: label_values(DCGM_FI_DEV_GPU_UTIL{instance="$node"}, gpu)
```

下拉选节点和 GPU，一个 Dashboard 看全集群。

## 告警面板

Grafana Unified Alerting 或沿用 Alertmanager：

```promql
max(DCGM_FI_DEV_GPU_TEMP) by (instance) > 85
```

## 与 K8s Pod 关联（进阶）

需 join 平台元数据（Pod 名、Namespace、用户），常见方案：
- 训练平台写入 labels
- 自定义 exporter 暴露 pod 标签

## 大屏建议布局

```
第一行：集群 GPU 总数 / 平均利用率 / 告警数
第二行：各节点温度热力图
第三行：Top N 显存占用 GPU
第四行：XID / NVLink 错误趋势
```

## 注意

- 指标名随 dcgm-exporter 版本可能变化，Import 后验证 PromQL
- 时间范围训练任务用 1h~24h，巡检用 5m

可视化让 DCGM 数据**对管理层和开发都可见**。
