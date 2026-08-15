---
title: etcd v3.7 抓取：Benchmarking etcd v2.1.0
date: 2026-09-13 10:24:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/benchmarks/etcd-2-1-0-alpha-benchmarks/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/benchmarks/etcd-2-1-0-alpha-benchmarks/>

---

## Physical machines

GCE n1-highcpu-2 machine type

1x dedicated local SSD mounted under /var/lib/etcd

1x dedicated slow disk for the OS

1.8 GB memory

2x CPUs

etcd version 2.1.0 alpha

## etcd Cluster

3 etcd members, each runs on a single machine

## Testing

Bootstrap another machine and use the
hey HTTP benchmark tool
to send requests to each etcd member. Check the
benchmark hacking guide
for detailed instructions.

## Performance

### reading one single key

### writing one single key

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Benchmarking etcd v2.1.0](https://etcd.io/docs/v3.7/benchmarks/etcd-2-1-0-alpha-benchmarks/)
