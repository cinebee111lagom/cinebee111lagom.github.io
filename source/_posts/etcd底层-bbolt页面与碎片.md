---
title: etcd 底层：bbolt 页面复制与碎片
date: 2026-09-12 09:21:00
tags:
  - etcd
  - bbolt
categories:
  - etcd v3.7 底层细节
---

bbolt 物理页 **不原地修改**：写时拷到新页，旧页在无只读事务引用后进 freelist。因此：

- 打开的 RO 事务看到一致历史视图
- RW 事务互斥
- 大 value 占连续多页；分配/回收导致 **碎片增大**，文件 **只增不缩**

只有 **defrag** 才会重写为新文件并截断体积。这与“逻辑上已 compaction”但 `du` 仍很大 的现象一致。

> 延伸阅读：[Persistent storage files](https://etcd.io/docs/v3.7/learning/persistent-storage-files/)

