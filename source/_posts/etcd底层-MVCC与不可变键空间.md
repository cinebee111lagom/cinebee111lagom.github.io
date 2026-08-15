---
title: etcd 底层：MVCC 与不可变键空间
date: 2026-09-12 09:01:00
tags:
  - etcd
  - MVCC
categories:
  - etcd v3.7 底层细节
---

etcd 面向 **低频更新、可靠 Watch、可回溯历史**。存储是多版本持久化 KV：**不原地改**，每次变更生成新结构，旧版本仍可访问/Watch，直到被压缩丢掉。

## 为何如此设计

- 便宜的历史与快照语义（“时间旅行”查询）
- Watch 可在连续历史窗口内可靠重放
- 用 compaction 控制无限增长

逻辑上键空间是扁平二进制键 + 字典序索引，范围查询便宜。

> 延伸阅读：[Data model](https://etcd.io/docs/v3.7/learning/data_model/)

