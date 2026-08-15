---
title: etcd v3.7 抓取：Benchmarking etcd v3
date: 2026-09-13 10:28:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/benchmarks/etcd-3-demo-benchmarks/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/benchmarks/etcd-3-demo-benchmarks/>

---

## Physical machines

GCE n1-highcpu-2 machine type

1x dedicated local SSD mounted under /var/lib/etcd

1x dedicated slow disk for the OS

1.8 GB memory

2x CPUs

etcd version 2.2.0

## etcd Cluster

1 etcd member running in v3 demo mode

## Testing

Use
etcd v3 benchmark tool
.

## Performance

### reading one single key

The performance is nearly the same as the one with empty server handler.

### reading one single key after putting

The performance with empty server handler is not affected by one put. So the
performance downgrade should be caused by storage package.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Benchmarking etcd v3](https://etcd.io/docs/v3.7/benchmarks/etcd-3-demo-benchmarks/)
