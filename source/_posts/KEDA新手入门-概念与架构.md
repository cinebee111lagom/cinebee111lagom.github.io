---
title: KEDA 新手入门：概念与架构
date: 2026-09-09 09:00:00
tags:
  - KEDA
  - Kubernetes
  - 入门
categories:
  - KEDA 新手入门
---

**KEDA**（Kubernetes Event-driven Autoscaling）按真实事件（队列、请求、指标等）伸缩工作负载，与 HPA 协同而非替代。

## 三个组件

| 组件 | 职责 |
|------|------|
| keda-operator | 管理 ScaledObject/HPA；负责 0↔1 伸缩 |
| keda-metrics-apiserver | 向 HPA 暴露外部指标 |
| keda-admission-webhooks | 校验 CR，避免错误配置上线 |

## 伸缩双轨

1. **0↔1**：operator 直接处理（有事件拉起，空闲缩到 0）
2. **1↔N**：交由 HPA，经 metrics-apiserver 读外部指标

注意：仅用 CPU/Memory 触发时，指标来自 metrics-server，**不支持 scale-to-zero**（无 Pod 就无指标）。

## 核心 CRD

- ScaledObject：Deployment/StatefulSet/自定义资源
- ScaledJob：按事件创建 Job
- TriggerAuthentication：外部源鉴权

> 官方文档（v2.20）：[Concepts](https://keda.sh/docs/2.20/concepts/)

