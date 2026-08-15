---
title: Dragonfly 集成 TorchServe 入门
date: 2026-09-07 11:50:00
tags:
  - Dragonfly
  - TorchServe
  - 入门
categories:
  - Dragonfly 新手入门
---

TorchServe 多实例同时拉取模型时，可用 Dragonfly 降低模型仓库压力。

## 要点

- 模型制品 URL 稳定（含版本）
- 推理节点 Peer 缓存命中后冷启动更快
- 与滚动发布结合：先预热再扩容

> 官方文档：[TorchServe](https://d7y.io/docs/next/operations/integrations/torchserve/)

