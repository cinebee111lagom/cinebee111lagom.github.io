---
title: etcd v3.7 抓取：How to delete keys
date: 2026-09-13 09:20:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/developer/how-to-delete-keys/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/developer/how-to-delete-keys/>

---

## Prerequisites

Install
etcd
and
etcdctl

etcd

etcdctl

## Add or delete keys

del
to remove the specified key or range of keys:

del

```
etcdctl del
$KEY
[
$END_KEY
]
```

### Options

```
--prefix
[=
false
]
: delete keys with matching prefix
--prev-kv
[=
false
]
:
return
deleted key-value pairs
--from-key
[=
false
]
: delete keys that are greater than or equal to the given key using byte compare
--range
[=
false
]
: delete range of keys without delay
```

### Options inherited from parent commands

```
--endpoints
=
"127.0.0.1:2379"
: gRPC endpoints
```

### Examples

```
etcdctl --endpoints
=
$ENDPOINTS
put key myvalue
etcdctl --endpoints
=
$ENDPOINTS
del key
etcdctl --endpoints
=
$ENDPOINTS
put k1 value1
etcdctl --endpoints
=
$ENDPOINTS
put k2 value2
etcdctl --endpoints
=
$ENDPOINTS
del k --prefix
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

> 完整与最新内容以官方文档为准：[How to delete keys](https://etcd.io/docs/v3.7/tasks/developer/how-to-delete-keys/)
