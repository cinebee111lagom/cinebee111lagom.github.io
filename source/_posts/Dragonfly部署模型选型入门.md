---
title: Dragonfly 部署模型选型入门
date: 2026-09-07 10:20:00
tags:
  - Dragonfly
  - 架构
  - 入门
categories:
  - Dragonfly 新手入门
---

功能取决于部署了哪些组件。先看矩阵再选型。

## 三种模型

| 模型 | 组件 | 典型场景 |
|------|------|----------|
| Lightweight | Scheduler + Seed + Peer | 只要 P2P |
| Lightweight + Redis | 上 + Redis | 持久化 Task / Cache |
| With Manager | 上 + Manager + MySQL + Redis | 控制台、OpenAPI、多集群 |

## 功能矩阵（摘要）

| 功能 | 轻量 | +Redis | +Manager |
|------|------|--------|----------|
| Task 分发 | 是 | 是 | 是 |
| Persistent task | 否 | 是 | 是 |
| dfctl 预热 | 是 | 是 | 是 |
| OpenAPI / Console 预热 | 否 | 否 | 是 |

> 官方文档：[Deployment Models](https://d7y.io/docs/next/operations/deployment/deployment-models/)

