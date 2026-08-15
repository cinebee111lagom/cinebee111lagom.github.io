---
title: Volcano 文档：Queue 队列概念
date: 2026-09-10 09:30:00
tags:
  - Volcano
  - Queue
categories:
  - Volcano 文档导读
---

Queue 是多租户资源隔离与共享的核心：配额、权重、借用/回收/抢占都围绕队列展开。

## 用途

- 按团队/业务划分资源池
- 配合 proportion/capacity 等插件做公平与保障
- Job 通过 `spec.queue` 归属队列

> 官方文档：[Queue](https://volcano.sh/zh-Hans/docs/Concepts/Queue)

