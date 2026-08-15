---
title: Dragonfly 参考：dfdaemon 配置
date: 2026-09-08 14:30:00
tags:
  - Dragonfly
  - dfdaemon
  - 配置
  - 参考
categories:
  - Dragonfly 进阶指南
---

dfdaemon 配置是性能与稳定性关键：download/upload 限速、分片并发、proxy、gc、scheduler 地址、Seed 模式等。

## 优先对齐

- bandwidthLimit
- concurrentPieceCount
- gc.taskTTL 与磁盘水位
- proxy 安全与 mirror 规则

> 官方文档：[dfdaemon config](https://d7y.io/docs/next/reference/configuration/client/dfdaemon/)

