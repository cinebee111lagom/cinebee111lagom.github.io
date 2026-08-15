---
title: etcd v3.7 抓取：Benchmarking etcd v2.2.0
date: 2026-09-13 10:25:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-benchmarks/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-benchmarks/>

---

## Physical Machines

GCE n1-highcpu-2 machine type

1x dedicated local SSD mounted as etcd data directory

1x dedicated slow disk for the OS

1.8 GB memory

2x CPUs

## etcd Cluster

3 etcd 2.2.0 members, each runs on a single machine.

Detailed versions:

```
etcd Version: 2.2.0
Git SHA: e4561dd
Go Version: go1.5
Go OS/Arch: linux/amd64
```

## Testing

Bootstrap another machine, outside of the etcd cluster, and run the
hey
HTTP benchmark tool
with a connection reuse patch to send requests to each etcd cluster member. See the
benchmark instructions
for the patch and the steps to reproduce our procedures.

hey

The performance is calculated through results of 100 benchmark rounds.

## Performance

### Single Key Read Performance

### Single Key Write Performance

## Performance Changes

Because etcd now records metrics for each API call, read QPS performance seems to see a minor decrease in most scenarios. This minimal performance impact was judged a reasonable investment for the breadth of monitoring and debugging information returned.

Write QPS to cluster leaders seems to be increased by a small margin. This is because the main loop and entry apply loops were decoupled in the etcd raft logic, eliminating several blocks between them.

Write QPS to all members seems to be increased by a significant margin, because followers now receive the latest commit index sooner, and commit proposals more quickly.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Benchmarking etcd v2.2.0](https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-benchmarks/)
