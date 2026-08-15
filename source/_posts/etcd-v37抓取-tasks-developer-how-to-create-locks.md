---
title: etcd v3.7 抓取：How to create locks
date: 2026-09-13 09:24:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/developer/how-to-create-locks/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/developer/how-to-create-locks/>

---

LOCK acquires a distributed mutex with a given name. Once the lock is acquired, it will be held until etcdctl is terminated.

## Prerequisites

Install
etcd
and
etcdctl

etcd

etcdctl

## Creating a lock

lock
for distributed lock:

lock

```
etcdctl --endpoints
=
$ENDPOINTS
lock mutex1
```

### Options

endpoints - defines a comma-delimited list of machine addresses in the cluster.

ttl - time out in seconds of lock session.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[How to create locks](https://etcd.io/docs/v3.7/tasks/developer/how-to-create-locks/)
