---
title: Dragonfly 整体架构入门
date: 2026-09-07 13:00:00
tags:
  - Dragonfly
  - 架构
  - 入门
categories:
  - Dragonfly 新手入门
---

定位：高效、稳定、安全、低成本的文件与镜像分发，作为云原生最佳实践方案之一。

## 子系统

### Manager

动态配置、集群关系、预热任务、保活、控制台、清缓存等。

### Scheduler

多特征选 Parent、构建调度 DAG、摘除异常 Peer、失败时通知回源、元数据支撑写文件与做种。

### Client（含 Seed）

dfget/gRPC 下载、多协议源、Seed 回源根节点、Registry Proxy、RDMA 等加速能力。

## 工作流（摘要）

首次下载：Scheduler 触发 Seed 回源 → 分片 → Peer 拉取并上报。  
再次下载：命中本地或从其他 Peer 并行拉分片。

> 官方文档：[Architecture](https://d7y.io/docs/next/operations/architecture/architecture/)

