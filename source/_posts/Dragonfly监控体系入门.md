---
title: Dragonfly 监控体系入门
date: 2026-09-07 12:30:00
tags:
  - Dragonfly
  - 监控
  - 入门
categories:
  - Dragonfly 新手入门
---

监控要覆盖 **控制面健康、调度质量、P2P 命中、回源与磁盘**。

## 分层

1. 组件存活与副本
2. 下载成功率 / 耗时
3. 回源比例（过高说明 P2P 未生效）
4. Seed/Peer 磁盘水位与 GC
5. 网络带宽

## 落地

- Prometheus 刮取各组件 `/metrics`
- Grafana 按集群/任务类型聚合
- 告警：调度失败飙升、回源占比异常、磁盘高水位

> 官方文档：[Monitoring](https://d7y.io/docs/next/operations/observability/monitoring/)

