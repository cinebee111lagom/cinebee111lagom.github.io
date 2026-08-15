---
title: Dragonfly 集成 Harbor 入门
date: 2026-09-07 11:10:00
tags:
  - Dragonfly
  - Harbor
  - 入门
categories:
  - Dragonfly 新手入门
---

Harbor 常作为企业 Registry。Dragonfly 可与其结合做 **镜像预热** 与拉取加速。

## 典型用法

- Peer Proxy 加速从 Harbor 拉镜像
- Manager 异步任务 + Harbor 触发预热（需 Manager 部署模型）

## 注意

- 预热目标镜像 tag/digest 明确
- 权限：预热账号最小权限
- 大镜像预热要错峰，避免打满 Seed 磁盘

> 官方文档：[Harbor](https://d7y.io/docs/next/operations/integrations/harbor/)

