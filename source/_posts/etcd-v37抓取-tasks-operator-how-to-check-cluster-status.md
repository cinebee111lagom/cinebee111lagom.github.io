---
title: etcd v3.7 抓取：How to check Cluster status
date: 2026-09-13 09:13:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/operator/how-to-check-cluster-status/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/operator/how-to-check-cluster-status/>

---

## Prerequisites

Install
etcd
and
etcdctl

etcd

etcdctl

## Check Overall Status

endpoint status
to check the overall status of each endpoint specified in
--endpoints
flag:

endpoint status

--endpoints

```
etcdctl endpoint status
(
--endpoints
=
$ENDPOINTS
|
--cluster
)
```

### Options

```
--cluster
[=
false
]
: use all endpoints from the cluster member list
```

## Check Health

endpoint health
to check the healthiness of each endpoint specified in
--endpoints
flag:

endpoint health

--endpoints

```
etcdctl endpoint health
(
--endpoints
=
$ENDPOINTS
|
--cluster
)
```

### Options

```
--cluster
[=
false
]
: use all endpoints from the cluster member list
```

## Check KV Hash

endpoint hashkv
to check the KV history hash of each endpoint specified in
--endpoints
flag:

endpoint hashkv

--endpoints

```
etcdctl endpoint hashkv
(
--endpoints
=
$ENDPOINTS
|
--cluster
)
[
rev
=
$REV
]
```

### Options

```
--cluster
[=
false
]
: use all endpoints from the cluster member list
--rev
=
0: maximum revision to
hash
(
default: latest revision
)
```

## Options inherited from parent commands

```
--endpoints
=
"127.0.0.1:2379"
: gRPC endpoints
-w, --write-out
=
"simple"
:
set
the output format
(
fields, json, protobuf, simple, table
)
```

### Examples

```
etcdctl --write-out
=
table --endpoints
=
$ENDPOINTS
endpoint status
+------------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
|
ENDPOINT
|
ID
|
VERSION
|
DB SIZE
|
IS LEADER
|
IS LEARNER
|
RAFT TERM
|
RAFT INDEX
|
RAFT APPLIED INDEX
|
ERRORS
|
+------------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
|
10.240.0.17:2379
|
4917a7ab173fabe7
|
3.5.0
|
45
kB
|
true
|
false
|
4
|
16726
|
16726
|
|
|
10.240.0.18:2379
|
59796ba9cd1bcd72
|
3.5.0
|
45
kB
|
false
|
false
|
4
|
16726
|
16726
|
|
|
10.240.0.19:2379
|
94df724b66343e6c
|
3.5.0
|
45
kB
|
false
|
false
|
4
|
16726
|
16726
|
|
+------------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------
|
```

```
etcdctl --endpoints
=
$ENDPOINTS
endpoint health
10.240.0.17:2379 is healthy: successfully committed proposal:
took
=
3.345431ms
10.240.0.19:2379 is healthy: successfully committed proposal:
took
=
3.767967ms
10.240.0.18:2379 is healthy: successfully committed proposal:
took
=
4.025451ms
```

```
etcdctl --cluster endpoint hashkv  --write-out
=
table
+------------------+------------+---------------+
|
ENDPOINT
|
HASH
|
HASH REVISION
|
+------------------+------------+---------------+
|
10.240.0.17:2379
|
3892279174
|
3
|
|
10.240.0.18:2379
|
3892279174
|
3
|
|
10.240.0.19:2379
|
3892279174
|
3
|
+------------------+------------+---------------+
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

> 完整与最新内容以官方文档为准：[How to check Cluster status](https://etcd.io/docs/v3.7/tasks/operator/how-to-check-cluster-status/)
