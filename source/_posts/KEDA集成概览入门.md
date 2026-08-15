---
title: KEDA 集成概览入门
date: 2026-09-09 10:50:00
tags:
  - KEDA
  - 集成
  - 入门
categories:
  - KEDA 新手入门
---

官方 Integrations 当前重点：

| 集成 | 用途 |
|------|------|
| Prometheus | 刮取 KEDA 自身指标 + Grafana 面板 |
| OpenTelemetry | 实验性：向 Collector 推送指标 |
| Istio | 在 mTLS/网格下让 KEDA 组件正常通信 |

先保证伸缩正确，再接入可观测与服务网格注解。

> 官方文档（v2.20）：[Integrations](https://keda.sh/docs/2.20/integrations/)

