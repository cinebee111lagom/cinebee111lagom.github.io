---
title: KEDA 扩缩到零与 HPA 协作入门
date: 2026-09-09 12:00:00
tags:
  - KEDA
  - HPA
  - 入门
categories:
  - KEDA 新手入门
---

KEDA 不替换 HPA：operator 创建/管理 HPA，并把外部指标喂给它。

## 记忆点

| 区间 | 谁负责 |
|------|--------|
| 0 → 1 / 1 → 0 | keda-operator |
| 1 → N | HPA + metrics-apiserver |

CPU/Memory 触发：HPA 直接问 metrics-server → **无法从 0 唤醒**。要 scale-to-zero 请用队列/Prometheus/外部事件等非纯资源触发。

还可开启 raw metrics gRPC（`RAW_METRICS_GRPC_PROTOCOL=enabled`）供第三方订阅内部指标。

> 官方文档（v2.20）：[Concepts](https://keda.sh/docs/2.20/concepts/)

