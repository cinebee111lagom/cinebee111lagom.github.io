---
title: Dragonfly 多集群轻量部署入门
date: 2026-09-07 09:40:00
tags:
  - Dragonfly
  - 多集群
  - 入门
categories:
  - Dragonfly 新手入门
---

多集群轻量模式：各集群部署 Scheduler / Seed / Peer，**不依赖统一 Manager**，适合先打通跨集群 P2P 分发路径。

## 适用

- 多个 K8s 集群都要镜像加速
- 暂不需要统一控制台

## 实践建议

- 明确每个集群的源站 / Registry 出口
- 统一镜像仓库与证书方案，避免各集群各拉各的源
- 跨集群网络时评估带宽与安全策略

> 官方文档：[Multi-cluster Lightweight](https://d7y.io/docs/next/getting-started/quick-start/multi-cluster-kubernetes/lightweight-deployment/)

