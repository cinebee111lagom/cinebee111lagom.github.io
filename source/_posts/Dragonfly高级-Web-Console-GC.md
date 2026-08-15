---
title: Dragonfly 高级：Web Console GC
date: 2026-09-08 12:25:00
tags:
  - Dragonfly
  - GC
  - 进阶
categories:
  - Dragonfly 进阶指南
---

控制台 GC 功能用于管理任务/缓存回收相关操作。

执行前确认：

- 非高峰
- 热点镜像仍有 Seed 副本或可回源
- 与 dfdaemon gc 阈值一致，避免反复抖动

> 官方文档：[Console GC](https://d7y.io/docs/next/advanced-guides/web-console/gc)

