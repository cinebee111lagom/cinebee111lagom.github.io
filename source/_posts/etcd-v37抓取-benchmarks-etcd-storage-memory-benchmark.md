---
title: etcd v3.7 抓取：Storage Memory Usage Benchmark
date: 2026-09-13 10:30:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/benchmarks/etcd-storage-memory-benchmark/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/benchmarks/etcd-storage-memory-benchmark/>

---

Two components of etcd storage consume physical memory. The etcd process allocates an
in-memory index
to speed key lookup. The process’s
page cache
, managed by the operating system, stores recently-accessed data from disk for quick re-use.

The in-memory index holds all the keys in a
B-tree
data structure, along with pointers to the on-disk data (the values). Each key in the B-tree may contain multiple pointers, pointing to different versions of its values. The theoretical memory consumption of the in-memory index can hence be approximated with the formula:

N * (c1 + avg_key_size) + N * (avg_versions_of_key) * (c2 + size_of_pointer)

where
c1
is the key metadata overhead and
c2
is the version metadata overhead.

c1

c2

The graph shows the detailed structure of the in-memory index B-tree.

```
In mem index

                               +------------+
                               | key || ... |
  +--------------+             |     ||     |
  |              |             +------------+
  |              |             | v1  || ... |
  |   disk    <----------------|     ||     | Tree Node
  |              |             +------------+
  |              |             | v2  || ... |
  |           <----------------+     ||     |
  |              |             +------------+
  +--------------+       +-----+    |   |   |
                         |     |    |   |   |
                         |     +------------+
                         |
                         |
                         ^
                      ------+
                      | ... |
                      |     |
                      +-----+
                      | ... | Tree Node
                      |     |
                      +-----+
                      | ... |
                      |     |
                      ------+
```

Page cache memory
is managed by the operating system and is not covered in detail in this document.

## Testing Environment

etcd version

git head
https://github.com/etcd-io/etcd/commit/776e9fb7be7eee5e6b58ab977c8887b4fe4d48db

GCE n1-standard-2 machine type

7.5 GB memory

2x CPUs

## In-memory index memory usage

In this test, we only benchmark the memory usage of the in-memory index. The goal is to find
c1
and
c2
mentioned above and to understand the hard limit of memory consumption of the storage.

c1

c2

We calculate the memory usage consumption via the Go runtime.ReadMemStats. We calculate the total allocated bytes difference before creating the index and after creating the index. It cannot perfectly reflect the memory usage of the in-memory index itself but can show the rough consumption pattern.

Based on the result, we can calculate
c1=120bytes
,
c2=30bytes
. We only need two sets of data to calculate
c1
and
c2
, since they are the only unknown variable in the formula. The
c1=120bytes
and
c2=30bytes
are the average value of the 4 sets of
c1
and
c2
we calculated. The key metadata overhead is still relatively nontrivial (50%) for small key-value pairs. However, this is a significant improvement over the old store, which had at least 1000% overhead.

c1=120bytes

c2=30bytes

c1

c2

c1=120bytes

c2=30bytes

c1

c2

## Overall memory usage

The overall memory usage captures how much RSS etcd consumes with the storage. The value size should have very little impact on the overall memory usage of etcd, since we keep values on disk and only retain hot values in memory, managed by the OS page cache.

Based on the result, we know the value size does not significantly impact the memory consumption. There is some minor increase due to more data held in the OS page cache.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Storage Memory Usage Benchmark](https://etcd.io/docs/v3.7/benchmarks/etcd-storage-memory-benchmark/)
