---
title: Volcano 文档：CronVolcanoJob 概念
date: 2026-09-10 09:25:00
tags:
  - Volcano
  - Cron
categories:
  - Volcano 文档导读
---

CronVolcanoJob 按 Cron 表达式周期创建 VolcanoJob，适合定时训练、批处理窗口作业。

## 实践要点

- 明确时区与并发策略（是否允许重叠）
- 失败重试与历史保留策略
- 队列配额要覆盖峰值并发 Job 数

> 官方文档：[CronVolcanoJob](https://volcano.sh/zh-Hans/docs/Concepts/CronVolcanoJob)

