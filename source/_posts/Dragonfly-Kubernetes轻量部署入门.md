---
title: Dragonfly Kubernetes 轻量部署入门
date: 2026-09-07 09:20:00
tags:
  - Dragonfly
  - Kubernetes
  - 入门
categories:
  - Dragonfly 新手入门
---

轻量部署只装 **Scheduler + Seed Client + Client**，不装 Manager 及其 MySQL/Redis。动态配置来自本地 `dynconfig.yaml`（ConfigMap）。

## 适用

- 小规模 K8s、边缘、CI
- 只需要 P2P 分发与 `dfctl` 预热

## 要点

- Client 通过 Scheduler Headless Service 发现调度器
- 无 Web Console / OpenAPI 预热（需 Manager 才有）
- 持久化 Task / Persistent Cache 需要额外 Redis

## 上线检查

- [ ] Scheduler 多副本（生产建议 ≥3）
- [ ] Seed Peer 磁盘容量够装热镜像
- [ ] Peer DaemonSet 覆盖业务节点

> 官方文档：[Lightweight Deployment](https://d7y.io/docs/next/getting-started/quick-start/kubernetes/lightweight-deployment/)

