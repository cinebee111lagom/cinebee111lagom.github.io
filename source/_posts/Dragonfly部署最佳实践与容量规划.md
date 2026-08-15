---
title: Dragonfly 部署最佳实践与容量规划
date: 2026-09-07 10:30:00
tags:
  - Dragonfly
  - 容量
  - 调优
  - 入门
categories:
  - Dragonfly 新手入门
---

按官方 Best Practices 做容量与性能基线。

## 容量粗算（官方量级）

| 组件 | 依据 | 生产副本 |
|------|------|----------|
| Manager | Peer 规模 | ≥3 |
| Scheduler | RPS | ≥3 |
| Seed Peer | RPS + 磁盘 | ≥3 |
| Peer | 节点本地缓存盘 | DaemonSet |

示例：约 1K Peer 时，Manager/Scheduler 约 8C16G 级起；Seed 磁盘可达 Ti 级。

## 性能调优

| 项 | 配置思路 |
|----|----------|
| 出站带宽 | upload.bandwidthLimit 对齐机器上行 |
| 入站带宽 | download.bandwidthLimit |
| 分片并发 | download.concurrentPieceCount |
| GC | taskTTL 与磁盘高/低水位 |

> 官方文档：[Deployment Best Practices](https://d7y.io/docs/next/operations/deployment/deployment-best-practices/)

