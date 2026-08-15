---
title: KEDA Scalers 概览入门
date: 2026-09-09 10:20:00
tags:
  - KEDA
  - Scaler
  - 入门
categories:
  - KEDA 新手入门
---

Scaler 负责：**判断是否激活**，以及向 HPA **提供自定义指标**。

## 分类（文档筛选维度）

Messaging、Datastore、Metrics、CI/CD、Apps、Scheduling、Kubernetes、Monitoring 等；含 Built-in 与 External。

## 实践建议

- 生产优先成熟内置 scaler（Kafka、RabbitMQ、Prometheus、AWS SQS…）
- 自定义需求用 External scaler
- 每个 trigger 写清 threshold/query 与鉴权引用
- 同一 Deployment 避免多个 ScaledObject 冲突（webhook 会拦）

> 官方文档（v2.20）：[Scalers](https://keda.sh/docs/2.20/scalers/)

