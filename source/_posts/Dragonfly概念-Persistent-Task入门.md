---
title: Dragonfly 概念：Persistent Task
date: 2026-09-08 09:10:00
tags:
  - Dragonfly
  - PersistentTask
  - 概念
categories:
  - Dragonfly 进阶指南
---

**Persistent Task** 将任务元数据持久化（通常依赖 Scheduler 侧 Redis），适合需要跨重启保留任务信息的场景。

## 前置

- 部署模型需 **Lightweight + Redis** 或 **With Manager**
- 纯轻量无 Redis 时无此能力

## 何时用

- 需要可查询的持久任务记录
- 与控制面/运维流程联动管理任务生命周期

> 官方文档：[Persistent Task](https://d7y.io/docs/next/concepts/persistent-task/)

