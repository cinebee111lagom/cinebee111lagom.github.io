---
title: KEDA 集成 Prometheus 指标入门
date: 2026-09-09 11:30:00
tags:
  - KEDA
  - Prometheus
  - 监控
  - 入门
categories:
  - KEDA 新手入门
---

各组件在 **8080/metrics** 暴露指标。

## Operator 关键指标

- `keda_build_info`
- `keda_scaler_active` / `keda_scaler_metrics_value`
- `keda_scaler_metrics_latency_seconds`
- `keda_scaler_detail_errors_total`
- `keda_scaled_object_errors_total` / `keda_scaled_job_errors_total`
- `keda_scaled_object_paused`
- HTTP 出站请求计数与耗时

Webhook：校验总数/错误；Metrics Server：gRPC 客户端与 apiserver 相关指标。

官方提供 Grafana 预置面板（按 namespace/scaledObject/scaler 等变量筛选）。未部署任何 scaler 时往往只见 `keda_build_info`。

> 官方文档（v2.20）：[Prometheus](https://keda.sh/docs/2.20/integrations/prometheus/)

