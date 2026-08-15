---
title: etcd 底层：Defrag 与空间回收
date: 2026-09-12 09:17:00
tags:
  - etcd
  - 维护
categories:
  - etcd v3.7 底层细节
---

Compaction 删除旧版本后，bbolt 文件可能仍占用空洞。**defrag** 重建后端以回收空间。

## 注意

- defrag 有 IO/耗时，跟在压缩之后、低峰执行
- 逐成员进行，观察健康
- 与 snapshot 备份策略分开规划

> 延伸阅读：[Maintenance](https://etcd.io/docs/v3.7/op-guide/maintenance/)

