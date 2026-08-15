---
title: etcd 底层：bbolt 关键 Buckets
date: 2026-09-12 09:22:00
tags:
  - etcd
  - bbolt
categories:
  - etcd v3.7 底层细节
---

`snap/db` 内分 bucket（随版本略有增减），常见包括：

| Bucket | 内容 |
|--------|------|
| `key` | MVCC 用户键（含 tombstone） |
| `lease` | 租约元数据 |
| `meta` | `consistent_index`、压缩进度等 |
| `members` / `members_removed` | 成员与已移除 ID |
| `auth` / `authUsers` / `authRoles` | 认证 |
| `alarm` | NOSPACE / CORRUPT 等告警 |
| `cluster` | 集群版本、降级意图等 |

排查可用官方提到的 `bbolt` / `etcd-dump-db` 等工具只读检查（生产慎用，先备份）。

> 延伸阅读：[Persistent storage files](https://etcd.io/docs/v3.7/learning/persistent-storage-files/)

