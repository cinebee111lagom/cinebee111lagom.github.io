---
title: Dragonfly 集成升级指南入门
date: 2026-09-08 10:10:00
tags:
  - Dragonfly
  - 升级
  - 入门
categories:
  - Dragonfly 新手入门
---

升级 Dragonfly 或其集成组件时，需保证 **运行时配置、Peer、Scheduler 版本** 兼容。

## 建议流程

1. 读发行说明与破坏性变更
2. 预发验证拉取与预热
3. 先控制面/调度，再滚动 Peer
4. 观察回源比与失败率

保留上一稳定 chart/values 以便回滚。

> 官方文档：[Upgrade](https://d7y.io/docs/next/operations/integrations/upgrade/)

