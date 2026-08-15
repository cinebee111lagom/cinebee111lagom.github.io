---
title: Volcano 文档：Scheduler Actions
date: 2026-09-10 10:25:00
tags:
  - Volcano
  - Scheduler
categories:
  - Volcano 文档导读
---

| Action | 作用 |
|--------|------|
| enqueue | 过滤后入队，pending → inqueue |
| allocate | 预选+优选绑定节点 |
| preempt | 同队列高优先级抢占 |
| reclaim | 按队列权重回收应得资源 |
| backfill | 尽量填满节点碎片资源 |

> 官方文档：[Actions](https://volcano.sh/zh-Hans/docs/Scheduler/Actions)

