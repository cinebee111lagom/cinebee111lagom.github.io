---
title: Dragonfly 链路追踪 Tracing 入门
date: 2026-09-07 12:40:00
tags:
  - Dragonfly
  - Tracing
  - 入门
categories:
  - Dragonfly 新手入门
---

分布式追踪用于定位「慢在调度、回源还是分片传输」。

## 用途

- 单次下载 Task 全链路耗时拆解
- 对比 Parent 选择是否合理
- 与指标互补，避免只看平均值

## 建议

- 采样率按环境区分（生产低采样）
- TraceID 与任务 ID 关联进日志

> 官方文档：[Tracing](https://d7y.io/docs/next/operations/observability/tracing/)

