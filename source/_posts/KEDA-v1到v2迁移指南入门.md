---
title: KEDA v1 到 v2 迁移指南入门
date: 2026-09-09 11:10:00
tags:
  - KEDA
  - 迁移
  - 入门
categories:
  - KEDA 新手入门
---

**同一集群不能同时跑 v1 与 v2**；先卸 v1（含旧 CRD）。

## 关键变化

| 项 | v2 |
|----|-----|
| API | `keda.sh/v1alpha1`（原 `keda.k8s.io`） |
| Deployment 缩放 | `scaleTargetRef.name`；`envSourceContainerName` |
| Job | 独立 **ScaledJob**，不再用 ScaledObject+scaleType |
| 触发器凭证 | 多用 `*FromEnv`；部分 scaler 字段重命名 |

RabbitMQ：`apiHost` → `host` + `protocol`；Kafka `authMode` → `sasl`/`tls` 等。TriggerAuthentication 同样改 apiVersion。

> 官方文档（v2.20）：[Migration](https://keda.sh/docs/2.20/migration/)

