---
title: Dragonfly 高级：Leech 模式
date: 2026-09-08 10:40:00
tags:
  - Dragonfly
  - Leech
  - 进阶
categories:
  - Dragonfly 进阶指南
---

Leech 相关能力用于控制 Peer **只下载少上传**（或限制贡献带宽）的行为，适合弱网上传或保护节点上行。

## 场景

- 边缘弱网上行
- 不想让业务节点承担过多做种
- 与带宽限速策略配合

调参后观察 upload traffic 与整体回源是否恶化。

> 官方文档：[Leech](https://d7y.io/docs/next/advanced-guides/leech/)

