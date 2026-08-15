---
title: KEDA CRD：ScaledObject 与 ScaledJob
date: 2026-09-09 09:10:00
tags:
  - KEDA
  - ScaledObject
  - 入门
categories:
  - KEDA 新手入门
---

## ScaledObject

把工作负载绑到事件源，声明 `scaleTargetRef`、副本上下限、`triggers` 等。

常用字段：`pollingInterval`、`cooldownPeriod`、`minReplicaCount`、`maxReplicaCount`。

## ScaledJob

面向批处理：按队列等事件创建 Job，完成后可清理历史（`successfulJobsHistoryLimit` / `failedJobsHistoryLimit`）。

## 选型

| 场景 | 用 |
|------|----|
| 常驻服务按负载扩副本 | ScaledObject |
| 一条消息/一批任务一个 Job | ScaledJob |

> 官方文档（v2.20）：[Concepts](https://keda.sh/docs/2.20/concepts/)

