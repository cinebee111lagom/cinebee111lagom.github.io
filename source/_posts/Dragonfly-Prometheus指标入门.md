---
title: Dragonfly Prometheus 指标入门
date: 2026-09-07 12:20:00
tags:
  - Dragonfly
  - Prometheus
  - 监控
  - 入门
categories:
  - Dragonfly 新手入门
---

Client / Seed / Scheduler / Manager 均暴露固定路径 **`/metrics`**。

## 重点指标（入门）

| 组件 | 关注 |
|------|------|
| Client | download/upload task、traffic、proxy、磁盘 |
| Scheduler | register/download peer、back-to-source、schedule 耗时、traffic |
| Manager | search scheduler cluster、create job |

另有 gRPC 指标（go-grpc-prometheus）。

## 实践

- 按 `task_type` / `host_type` 分面板
- 回源失败与下载失败分开展示

> 官方文档：[Prometheus Metrics](https://d7y.io/docs/next/operations/observability/prometheus-metrics/)

