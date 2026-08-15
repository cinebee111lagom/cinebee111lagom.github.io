---
title: Dragonfly 概念：Persistent Cache Task
date: 2026-09-08 09:20:00
tags:
  - Dragonfly
  - PersistentCache
  - 概念
categories:
  - Dragonfly 进阶指南
---

**Persistent Cache Task** 面向可持久化的缓存任务，元数据同样依赖 Redis（及相应部署模型）。

## 与普通 Task 区别（入门理解）

| | 普通 Task | Persistent Cache Task |
|---|-----------|------------------------|
| 元数据持久化 | 有限/按部署 | 是（需 Redis） |
| 控制台资源 | Task | Persistent Cache Task |
| 适用 | 常规分发 | 需长期管理的缓存任务 |

生产启用前对照 Deployment Models 功能矩阵。

> 官方文档：[Persistent Cache Task](https://d7y.io/docs/next/concepts/persistent-cache-task/)

