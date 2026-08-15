---
title: Dragonfly 高级：Rate Limit 限速
date: 2026-09-08 11:00:00
tags:
  - Dragonfly
  - 限速
  - 进阶
categories:
  - Dragonfly 进阶指南
---

限速保护节点网卡与源站，避免 P2P/回源打满带宽。

## 常见维度

- Peer 上传/下载 bandwidthLimit
- 并发分片数
- 与 Best Practices 中的入站/出站配置一致

生产按网卡规格设上限，压测后再放开。

> 官方文档：[Rate Limit](https://d7y.io/docs/next/advanced-guides/rate-limit/)

