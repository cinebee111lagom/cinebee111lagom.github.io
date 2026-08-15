---
title: Volcano 文档：Scheduler 场景
date: 2026-09-10 10:30:00
tags:
  - Volcano
  - Scheduler
categories:
  - Volcano 文档导读
---

官方 Scenario 说明不同业务场景下如何组合 actions/plugins（训练齐套、队列公平、混部等）。

选型建议：先明确是否必须 Gang、是否多租户配额、是否 GPU 共享，再裁剪 `volcano-scheduler.conf`。

> 官方文档：[Scenario](https://volcano.sh/zh-Hans/docs/Scheduler/Scenario)

