---
title: Dragonfly Scheduler 组件入门
date: 2026-09-07 13:20:00
tags:
  - Dragonfly
  - Scheduler
  - 入门
categories:
  - Dragonfly 新手入门
---

Scheduler 是 P2P 调度核心。

## 职责

- 多特征智能调度，选择最优 Parent
- 构建调度 DAG
- 基于评估摘除异常 Peer
- 调度失败时通知回源
- 元数据存储以支持写文件与 seeding

## 运维关注

- 调度耗时与并发调度数
- 回源启动次数（异常升高需排查）
- 多副本与反亲和

> 官方文档：[Scheduler](https://d7y.io/docs/next/operations/architecture/components/scheduler/)

