---
title: Dragonfly Manager 组件入门
date: 2026-09-07 13:10:00
tags:
  - Dragonfly
  - Manager
  - 入门
categories:
  - Dragonfly 新手入门
---

Manager 是可选控制面。

## 职责

- 存储并下发动态配置
- 维护 Seed Peer 集群与 Scheduler 集群关系
- 异步任务（如结合 Harbor 的镜像预热）
- 与 Scheduler/Seed 保活
- 为 Client 过滤最优 Scheduler 集群
- Web Console、清 P2P 任务缓存

## 依赖

通常需要 MySQL + Redis。轻量部署可不装 Manager。

> 官方文档：[Manager](https://d7y.io/docs/next/operations/architecture/components/manager/)

