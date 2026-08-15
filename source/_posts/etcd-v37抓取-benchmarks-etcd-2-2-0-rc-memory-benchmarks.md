---
title: etcd v3.7 抓取：Benchmarking etcd v2.2.0-rc-memory
date: 2026-09-13 10:27:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-rc-memory-benchmarks/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-rc-memory-benchmarks/>

---

## Physical machine

GCE n1-standard-2 machine type

1x dedicated local SSD mounted under /var/lib/etcd

1x dedicated slow disk for the OS

7.5 GB memory

2x CPUs

## etcd

```
etcd Version: 2.2.0-rc.0+git
Git SHA: 103cb5c
Go Version: go1.5
Go OS/Arch: linux/amd64
```

## Testing

Start 3-member etcd cluster, each of which uses 2 cores.

The length of key name is always 64 bytes, which is a reasonable length of average key bytes.

## Memory Maximal Usage

etcd may use maximal memory if one follower is dead and the leader keeps sending snapshots.

max RSS
is the maximal memory usage recorded in 3 runs.

max RSS

## Data Size Threshold

When etcd reaches data size threshold, it may trigger leader election easily and drop part of proposals.

For most cases, the etcd cluster should work smoothly if it doesn’t hit the threshold. If it doesn’t work well due to insufficient resources, decrease its data size.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Benchmarking etcd v2.2.0-rc-memory](https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-rc-memory-benchmarks/)
