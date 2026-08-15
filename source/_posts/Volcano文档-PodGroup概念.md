---
title: Volcano 文档：PodGroup 概念
date: 2026-09-10 09:35:00
tags:
  - Volcano
  - PodGroup
categories:
  - Volcano 文档导读
---

PodGroup 将一组相关 Pod 作为整体调度单元，支撑 Gang（全部/最小数量齐套再开跑）等语义。

vcjob 通常会关联/创建 PodGroup；理解 PodGroup 有助于排查「一直 pending、minAvailable 不满足」类问题。

> 官方文档：[PodGroup](https://volcano.sh/zh-Hans/docs/Concepts/podgroup)

