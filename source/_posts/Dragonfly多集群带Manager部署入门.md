---
title: Dragonfly 多集群带 Manager 部署入门
date: 2026-09-07 09:50:00
tags:
  - Dragonfly
  - 多集群
  - Manager
  - 入门
categories:
  - Dragonfly 新手入门
---

多集群 + Manager：由 Manager 维护 **Scheduler 集群 / Seed Peer 集群关系**，并提供控制台与 OpenAPI。

## 价值

- 统一查看多集群状态
- 跨集群预热与任务管理
- 动态配置集中下发

## 注意

- Manager 成为关键控制面，需做好 HA 与备份
- 客户端选簇由 Manager 过滤最优 Scheduler 集群
- 变更窗口同时覆盖控制面与各数据面集群

> 官方文档：[Multi-cluster with Manager](https://d7y.io/docs/next/getting-started/quick-start/multi-cluster-kubernetes/deployment-with-manager/)

