---
title: Dragonfly 快速开始概览
date: 2026-09-07 09:10:00
tags:
  - Dragonfly
  - 入门
categories:
  - Dragonfly 新手入门
---

快速开始按部署形态分为 **单集群 Kubernetes** 与 **多集群 Kubernetes**，各自又分轻量部署与带 Manager 部署。

## 路径选择

| 目标 | 推荐入口 |
|------|----------|
| 先跑通 P2P | K8s 轻量部署 |
| 要控制台 / OpenAPI / 多集群管理 | 带 Manager 部署 |
| 跨多个 K8s 集群 | Multi-cluster 文档 |

## 建议顺序

1. 读清 Deployment Models 功能矩阵
2. 用 Helm 装一套轻量集群
3. 验证镜像通过 Peer Proxy 拉取
4. 再按需加 Manager、Redis、多集群

## 验收标准

- Scheduler / Seed Peer / Peer 健康
- 二次拉取同一镜像明显走 P2P（源站流量下降）
- `/metrics` 可刮取

> 官方文档：[Quick Start](https://d7y.io/docs/next/getting-started/quick-start)

