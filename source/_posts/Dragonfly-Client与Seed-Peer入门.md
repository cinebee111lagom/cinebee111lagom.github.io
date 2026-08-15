---
title: Dragonfly Client 与 Seed Peer 入门
date: 2026-09-07 13:30:00
tags:
  - Dragonfly
  - Client
  - SeedPeer
  - 入门
categories:
  - Dragonfly 新手入门
---

Client（dfdaemon）提供上传下载；开启 Seed 模式后可作为集群 **根 Peer** 回源。

## 能力

| 能力 | 说明 |
|------|------|
| dfget / gRPC | 下载任务 |
| 多协议源 | HTTP/HTTPS 等 |
| Seed Peer | 回源根节点 |
| Proxy | Registry mirror 与其它 HTTP 后端 |
| RDMA | 加速高速网络场景（如模型装载） |

## 运维

- Seed 磁盘与带宽显著大于普通 Peer
- 配置 upload/download 带宽上限与分片并发
- 监控磁盘占用与 GC

> 官方文档：[Client](https://d7y.io/docs/next/operations/architecture/components/client/)

