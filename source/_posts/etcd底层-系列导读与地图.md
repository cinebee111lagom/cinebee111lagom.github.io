---
title: etcd 底层细节：系列导读与地图
date: 2026-09-12 09:00:00
tags:
  - etcd
  - 底层
  - 入门
categories:
  - etcd v3.7 底层细节
---

本系列补充 **etcd v3.7 文档导读** 未展开的实现层：MVCC、B+树、WAL、Raft 时序、读写路径、Watch/Lease 语义与磁盘/网络敏感点。

## 地图

| 主题 | 关键词 |
|------|--------|
| 数据面 | revision、generation、tombstone、compaction |
| 存储面 | bbolt B+tree、内存 btree 索引、WAL/snap |
| 共识面 | Raft 提案、心跳/选举、Learner |
| 访问面 | 线性读 vs 可串行化读、Watch 保证 |
| 运维面 | fsync、quota、defrag、快照 |

配合官方 Learning / Tuning / API guarantees 阅读。

> 延伸阅读：[Data model](https://etcd.io/docs/v3.7/learning/data_model/)

