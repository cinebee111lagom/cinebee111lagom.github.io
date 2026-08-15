---
title: KEDA 集成 OpenTelemetry 入门（实验性）
date: 2026-09-09 11:40:00
tags:
  - KEDA
  - OpenTelemetry
  - 入门
categories:
  - KEDA 新手入门
---

Operator 可向 OTel Collector **推送**指标（实验特性）。

## 开启

- args：`--enable-opentelemetry-metrics=true`
- env：`OTEL_EXPORTER_OTLP_ENDPOINT`（如 `http://otel-collector:4318`）
- 可选 `OTEL_EXPORTER_OTLP_PROTOCOL` 等标准 OTLP 变量

指标语义与 Prometheus 导出类似（`keda.scaler.active`、`keda.scaler.metrics.value` 等）。部分旧指标名已弃用，升级时对照文档。

> 官方文档（v2.20）：[OpenTelemetry](https://keda.sh/docs/2.20/integrations/opentelemetry/)

