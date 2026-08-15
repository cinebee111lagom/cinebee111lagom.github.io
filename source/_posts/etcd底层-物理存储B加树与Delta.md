---
title: etcd 底层：物理存储 B+ 树与 Delta
date: 2026-09-12 09:04:00
tags:
  - etcd
  - 存储
categories:
  - etcd v3.7 底层细节
---

物理层用持久化 **B+tree**（bbolt）存 KV。每个 revision 只存相对上一 revision 的 **delta**，一个 revision 可对应树中多个 key。

## 物理 key 三元组

`(major, sub, type)`

| 字段 | 含义 |
|------|------|
| major | 该变更所在 store revision |
| sub | 同 revision 内区分不同用户键 |
| type | 可选后缀（如 `t` 表示 tombstone） |

树按字节序排列 → 按 revision 范围扫 delta 很快，便于从 r1 追到 r2。Compaction 删除过期物理 KV。

> 延伸阅读：[Data model](https://etcd.io/docs/v3.7/learning/data_model/)

