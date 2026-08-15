---
title: etcd 底层：Key 的 Generation 与 Tombstone
date: 2026-09-12 09:03:00
tags:
  - etcd
  - MVCC
categories:
  - etcd v3.7 底层细节
---

一个 key 从创建到删除是一代 **generation**。

- **创建**：version 从 1 起（当前 revision 上不存在则新建）
- **每次修改**：同代内 version 单调 +1
- **删除**：写 **tombstone**，结束当前代，version 置 0

Compaction 后：在 compact revision 之前已结束的 generation 会被清掉；compact 之前的旧值除最新外也会被移除。

理解 tombstone 有助于解释：删除后短暂仍可见历史、压缩后彻底消失。

> 延伸阅读：[Data model](https://etcd.io/docs/v3.7/learning/data_model/)

