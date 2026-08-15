---
title: Dragonfly 高级：Web Console 审计与 GC
date: 2026-09-08 12:20:00
tags:
  - Dragonfly
  - Audit
  - GC
  - 进阶
categories:
  - Dragonfly 进阶指南
---

## Audit

审计记录谁做了预热、删除、配置变更，便于追责与合规。

## GC

通过控制台触发或查看垃圾回收相关操作，释放无用任务缓存；需与 Peer 侧 `gc` 策略协同，避免误删热点。

> 官方文档：[Audit](https://d7y.io/docs/next/advanced-guides/web-console/audit)

