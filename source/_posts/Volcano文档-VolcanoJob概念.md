---
title: Volcano 文档：VolcanoJob 概念
date: 2026-09-10 09:20:00
tags:
  - Volcano
  - VolcanoJob
categories:
  - Volcano 文档导读
---

vcjob（`batch.volcano.sh/v1alpha1`）相对 K8s Job 增强：可指定调度器、minAvailable、多 task、生命周期策略、队列、优先级等。

## 关键字段

| 字段 | 含义 |
|------|------|
| schedulerName | 默认 volcano |
| minAvailable | 至少多少 Pod Running 才算正常 |
| tasks | 多角色副本与模板 |
| queue / priorityClassName | 队列与优先级 |
| plugins | ssh/env/svc 等 |
| policies / maxRetry | 生命周期与重试 |

状态含 pending、running、completed、failed、aborted 等。适合 TF/PyTorch/大数据批处理。

> 官方文档：[VolcanoJob](https://volcano.sh/zh-Hans/docs/Concepts/VolcanoJob)

