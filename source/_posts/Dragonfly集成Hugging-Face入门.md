---
title: Dragonfly 集成 Hugging Face 入门
date: 2026-09-07 11:20:00
tags:
  - Dragonfly
  - HuggingFace
  - AI
  - 入门
categories:
  - Dragonfly 新手入门
---

大模型权重从 Hugging Face 拉取时，多机同时下载极易打满出口。Dragonfly 用于 **模型文件 P2P 分发**。

## 价值

- 训练/推理节点共享已下载分片
- 降低公网与对象存储费用

## 实践建议

- 固定模型 revision / commit，保证 Task 一致
- 结合本地缓存盘与 GC 策略
- 与 HF_ENDPOINT / 镜像站策略统一，避免缓存碎片

> 官方文档：[Hugging Face](https://d7y.io/docs/next/operations/integrations/hugging-face/)

