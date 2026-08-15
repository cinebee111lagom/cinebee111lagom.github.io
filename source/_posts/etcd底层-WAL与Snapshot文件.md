---
title: etcd 底层：WAL 与 Snapshot 文件
date: 2026-09-12 09:07:00
tags:
  - etcd
  - WAL
categories:
  - etcd v3.7 底层细节
---

Raft 日志追加到 WAL；定期做 snapshot 截断旧日志，避免日志无限大。

## 两套“快照”别混

| 类型 | 用途 |
|------|------|
| Raft/内部 snapshot | 截断 WAL、成员追赶 |
| `etcdctl snapshot save` | 运维备份/灾难恢复 |

Tuning 中 `--snapshot-count` 影响多久做一次内部 snapshot（变更次数阈值）。高写入集群可下调以控内存/磁盘，但过频也有开销。

数据目录内文件勿手工乱删；损坏时按 Data corruption / Recovery 流程处理。

> 延伸阅读：[Persistent storage](https://etcd.io/docs/v3.7/learning/persistent-storage-files/)

