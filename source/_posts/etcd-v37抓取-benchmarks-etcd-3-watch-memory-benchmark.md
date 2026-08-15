---
title: etcd v3.7 抓取：Watch Memory Usage Benchmark
date: 2026-09-13 10:29:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/benchmarks/etcd-3-watch-memory-benchmark/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/benchmarks/etcd-3-watch-memory-benchmark/>

---

The watch features are under active development, and their memory usage may change as that development progresses. We do not expect it to significantly increase beyond the figures stated below.

A primary goal of etcd is supporting a very large number of watchers doing a massively large amount of watching. etcd aims to support O(10k) clients, O(100K) watch streams (O(10) streams per client) and O(10M) total watchings (O(100) watching per stream). The memory consumed by each individual watching accounts for the largest portion of etcd’s overall usage, and is therefore the focus of current and future optimizations.

Three related components of etcd watch consume physical memory: each
grpc.Conn
, each watch stream, and each instance of the watching activity.
grpc.Conn
maintains the actual TCP connection and other gRPC connection state. Each
grpc.Conn
consumes O(10kb) of memory, and might have multiple watch streams attached.

grpc.Conn

Each watch stream is an independent HTTP2 connection which consumes another O(10kb) of memory.
Multiple watchings might share one watch stream.

Watching is the actual struct that tracks the changes on the key-value store. Each watching should only consume < O(1kb).

```
+-------+
                                          | watch |
                              +---------> | foo   |
                              |           +-------+
                       +------+-----+
                       |   stream   |
      +--------------> |            |
      |                +------+-----+     +-------+
      |                       |           | watch |
      |                       +---------> | bar   |
+-----+------+                            +-------+
|            |         +------------+
|   conn     +-------> |   stream   |
|            |         |            |
+-----+------+         +------------+
      |
      |
      |
      |                +------------+
      +--------------> |   stream   |
                       |            |
                       +------------+
```

The theoretical memory consumption of watch can be approximated with the formula:
memory = c1 * number_of_conn + c2 * avg_number_of_stream_per_conn + c3 * avg_number_of_watch_stream

memory = c1 * number_of_conn + c2 * avg_number_of_stream_per_conn + c3 * avg_number_of_watch_stream

## Testing Environment

etcd version

git head
https://github.com/etcd-io/etcd/commit/185097ffaa627b909007e772c175e8fefac17af3

GCE n1-standard-2 machine type

7.5 GB memory

2x CPUs

## Overall memory usage

The overall memory usage captures how much
RSS
etcd consumes with the client watchers. While the result may vary by as much as 10%, it is still meaningful, since the goal is to learn about the rough memory usage and the pattern of allocations.

With the benchmark result, we can calculate roughly that
c1 = 17kb
,
c2 = 18kb
and
c3 = 350bytes
. So each additional client connection consumes 17kb of memory and each additional stream consumes 18kb of memory, and each additional watching only cause 350bytes. A single etcd server can maintain millions of watchings with a few GB of memory in normal case.

c1 = 17kb

c2 = 18kb

c3 = 350bytes

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Watch Memory Usage Benchmark](https://etcd.io/docs/v3.7/benchmarks/etcd-3-watch-memory-benchmark/)
