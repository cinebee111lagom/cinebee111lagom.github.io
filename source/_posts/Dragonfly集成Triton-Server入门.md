---
title: Dragonfly 集成 Triton Server 入门
date: 2026-09-07 12:00:00
tags:
  - Dragonfly
  - Triton
  - 入门
categories:
  - Dragonfly 新手入门
---

NVIDIA Triton 多副本加载大模型/多模型仓库时，Dragonfly 可加速模型文件到达节点。

## 实践

- 模型仓库（对象存储/HTTP）经 Peer 分发
- GPU 节点磁盘规划给模型缓存
- 发布前预热，避免尖峰回源

> 官方文档：[Triton Server](https://d7y.io/docs/next/operations/integrations/triton-server/)

