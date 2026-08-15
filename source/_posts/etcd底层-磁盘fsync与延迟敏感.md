---
title: etcd 底层：磁盘 fsync 与延迟敏感
date: 2026-09-12 09:13:00
tags:
  - etcd
  - 磁盘
categories:
  - etcd v3.7 底层细节
---

提案必须落盘，**etcd 对磁盘延迟极度敏感**。同盘其它进程打满 IO → fsync 变长 → 丢心跳 → 请求超时甚至短暂丢主。

## 实践

- 数据目录用专用 SSD
- Linux 可用 `ionice` 提高 etcd IO 优先级
- 监控 WAL fsync 耗时分位数
- CPU governor 可用 performance 降低调度抖动

跨机房部署时，要把 **磁盘 RTT + 网络 RTT** 一起算进超时预算。

> 延伸阅读：[Tuning](https://etcd.io/docs/v3.7/tuning/)

