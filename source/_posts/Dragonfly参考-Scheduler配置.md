---
title: Dragonfly 参考：Scheduler 配置
date: 2026-09-08 14:20:00
tags:
  - Dragonfly
  - Scheduler
  - 配置
  - 参考
categories:
  - Dragonfly 进阶指南
---

Scheduler 配置包括服务监听、动态配置来源（Manager 或本地 dynconfig）、Redis、调度算法相关项等。

轻量模式重点检查 `dynconfig` 与 scheduler Service 发现；Manager 模式检查与控制面连通。

> 官方文档：[Scheduler config](https://d7y.io/docs/next/reference/configuration/scheduler/)

