---
title: Volcano 文档：架构组件
date: 2026-09-10 09:05:00
tags:
  - Volcano
  - 架构
categories:
  - Volcano 文档导读
---

Volcano 主要由四部分组成：

| 组件 | 职责 |
|------|------|
| Scheduler | 通过 action + plugin 为 Job 选节点 |
| ControllerManager | Queue / PodGroup / VCJob 生命周期 |
| Admission | CRD API 校验 |
| vcctl | 命令行客户端 |

与 default-scheduler 相比，强调 **Job 级多种调度算法**。

> 官方文档：[Architecture](https://volcano.sh/zh-Hans/docs/Home/Architecture)

