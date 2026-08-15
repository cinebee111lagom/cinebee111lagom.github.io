---
title: etcd v3.7 抓取：Benchmarking etcd v2.2.0-rc
date: 2026-09-13 10:26:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-rc-benchmarks/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-rc-benchmarks/>

---

## Physical machine

GCE n1-highcpu-2 machine type

1x dedicated local SSD mounted under /var/lib/etcd

1x dedicated slow disk for the OS

1.8 GB memory

2x CPUs

## etcd Cluster

3 etcd 2.2.0-rc members, each runs on a single machine.

Detailed versions:

```
etcd Version: 2.2.0-alpha.1+git
Git SHA: 59a5a7e
Go Version: go1.4.2
Go OS/Arch: linux/amd64
```

Also, we use 3 etcd 2.1.0 alpha-stage members to form cluster to get base performance. etcd’s commit head is at
c7146bd5
, which is the same as the one that we use in
etcd 2.1 benchmark
.

## Testing

Bootstrap another machine and use the
hey HTTP benchmark tool
to send requests to each etcd member. Check the
benchmark hacking guide
for detailed instructions.

## Performance

### reading one single key

### writing one single key

### performance changes explanation

read QPS in most scenarios is decreased by 5~8%. The reason is that etcd records store metrics for each store operation. The metrics is important for monitoring and debugging, so this is acceptable.

write QPS to leader is increased by 20~30%. This is because we decouple raft main loop and entry apply loop, which avoids them blocking each other.

write QPS to all servers is increased by 30~80% because follower could receive latest commit index earlier and commit proposals faster.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Benchmarking etcd v2.2.0-rc](https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-rc-benchmarks/)
