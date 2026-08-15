---
title: Dragonfly 集成 Git LFS 入门
date: 2026-09-07 11:40:00
tags:
  - Dragonfly
  - Git-LFS
  - 入门
categories:
  - Dragonfly 新手入门
---

Git LFS 大文件在 CI 与开发机上重复拉取成本高，可通过 Dragonfly 加速 LFS 对象分发。

## 场景

- 多 Job 并发 clone 同一大仓
- 数据集以 LFS 形式存放

## 建议

- 代理或下载入口统一走 Peer
- 关注鉴权头透传与 HTTPS

> 官方文档：[Git LFS](https://d7y.io/docs/next/operations/integrations/git-lfs/)

