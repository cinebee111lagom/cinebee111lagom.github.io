---
title: etcd 底层：consistent_index 与副本追赶
date: 2026-09-12 09:23:00
tags:
  - etcd
  - Raft
  - 存储
categories:
  - etcd v3.7 底层细节
---

`meta.consistent_index` 表示 **已 apply 到 bbolt 的最后 WAL 偏移**。副本过落后，leader 可要求其从 `*.snap.db` 恢复，再继续追 WAL。

启动时若发现更新的 `.snap.db` 索引新于当前 `snap/db` 的 consistent_index，会走相应恢复逻辑。

运维含义：备份恢复、成员替换后要确认各成员 apply 进度接近，而不是只看进程在跑。

> 延伸阅读：[Persistent storage files](https://etcd.io/docs/v3.7/learning/persistent-storage-files/)

