---
title: Dragonfly 高级：Open API 预热
date: 2026-09-08 11:30:00
tags:
  - Dragonfly
  - OpenAPI
  - Preheat
  - 进阶
categories:
  - Dragonfly 进阶指南
---

有 Manager 时，可通过 Open API 创建预热任务：Manager 下发到 Scheduler，再触发 Seed/Peer 下载。

## 流程

1. 使用 PAT 调用预热 API
2. 指定镜像/文件与 scope
3. 查询 Job 状态直至完成
4. 再滚动业务，享受缓存命中

适合与 Harbor webhook / CD 流水线集成。

> 官方文档：[Open API Preheat](https://d7y.io/docs/next/advanced-guides/open-api/preheat/)

