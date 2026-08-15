---
title: Volcano 文档：Scheduler 概览
date: 2026-09-10 10:20:00
tags:
  - Volcano
  - Scheduler
categories:
  - Volcano 文档导读
---

Scheduler = **actions**（调度环节动作）+ **plugins**（算法实现），可扩展自定义。

## 工作流

1. 观察并缓存 Job  
2. 开启会话  
3. 未调度 Job 入待调度队列  
4. 依次 enqueue → allocate → preempt → reclaim → backfill 等  
5. 关闭会话  

配置在 `volcano-scheduler-configmap`（`actions` 顺序即执行顺序）。

> 官方文档：[Scheduler Overview](https://volcano.sh/zh-Hans/docs/Scheduler/Overview)

