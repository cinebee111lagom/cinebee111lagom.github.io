---
title: etcd 底层：内存 B-tree 二级索引
date: 2026-09-12 09:05:00
tags:
  - etcd
  - 存储
categories:
  - etcd v3.7 底层细节
---

除持久 B+tree 外，etcd 维护 **内存 btree 二级索引**：

- 索引 key = 用户可见的逻辑 key
- 值 = 指向持久 B+tree 中最新修改的指针

查询路径概览：内存索引定位 revision 信息 → 用 revision 去持久树取 value。

Compaction 会清理失效指针。这也解释了：**大历史未压缩** 时内存与磁盘都会涨。

> 延伸阅读：[Data model](https://etcd.io/docs/v3.7/learning/data_model/)

