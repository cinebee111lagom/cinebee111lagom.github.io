---
title: Dragonfly Kubernetes 带 Manager 部署入门
date: 2026-09-07 09:30:00
tags:
  - Dragonfly
  - Kubernetes
  - Manager
  - 入门
categories:
  - Dragonfly 新手入门
---

在轻量组件之外增加 **Manager + MySQL + Redis**，获得控制面能力。

## 多出来的能力

| 能力 | 说明 |
|------|------|
| Web Console | 可视化管理 |
| Open API | 自动化预热/任务 |
| Preheat 任务 | 与 Harbor 等联动 |
| 多集群关系 | 统一纳管 |
| PAT | 个人访问令牌 |

## 部署注意

- Manager 生产建议 ≥3 副本
- MySQL/Redis 走高可用或托管服务
- 先验证控制台登录与集群注册，再开预热 Job

> 官方文档：[Deployment with Manager](https://d7y.io/docs/next/getting-started/quick-start/kubernetes/deployment-with-manager/)

