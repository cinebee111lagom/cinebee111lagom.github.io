---
title: Dragonfly 集成 Stargz 入门
date: 2026-09-08 10:00:00
tags:
  - Dragonfly
  - Stargz
  - 入门
categories:
  - Dragonfly 新手入门
---

eStargz / Stargz 支持懒加载镜像层；结合 Dragonfly 可加速层数据在集群内分发。

## 要点

- 镜像需转换为兼容格式
- 运行时 snapshotter 与 Dragonfly 代理协同
- 适合大规模节点同时启动同类镜像的场景

> 官方文档：[Stargz](https://d7y.io/docs/next/operations/integrations/container-runtime/stargz/)

