---
title: etcd v3.7 抓取：How to save the database
date: 2026-09-13 09:14:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/operator/how-to-save-database/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/operator/how-to-save-database/>

---

## Pre-requisites

Install etcdctl, etcdutl

Setup a local cluster

## Snapshot a database

snapshot
to save point-in-time snapshot of etcd database:

snapshot

```
etcdctl --endpoints
=
$ENDPOINT
snapshot save DB_NAME
```

### Global Options

#### etcdctl

```
--endpoints
=[
127.0.0.1:2379
]
, gRPC endpoints
```

Snapshot can only be requested from one etcd node, so
--endpoints
flag should contain only one endpoint.

--endpoints

#### etcdutl

```
-w, --write-out string
set
the output format
(
fields, json, protobuf, simple, table
)
(
default
"simple"
)
```

### Example

```
ENDPOINTS
=
$HOST_1
:2379
etcdctl --endpoints
=
$ENDPOINTS
snapshot save my.db
Snapshot saved at my.db
```

```
etcdutl --write-out
=
table snapshot status my.db
+---------+----------+------------+------------+
|
HASH
|
REVISION
|
TOTAL KEYS
|
TOTAL SIZE
|
+---------+----------+------------+------------+
|
c55e8b8
|
9
|
13
|
25
kB
|
+---------+----------+------------+------------+
```

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[How to save the database](https://etcd.io/docs/v3.7/tasks/operator/how-to-save-database/)
