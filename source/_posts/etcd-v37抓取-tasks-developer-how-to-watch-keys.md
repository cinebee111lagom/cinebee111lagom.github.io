---
title: etcd v3.7 抓取：How to watch keys
date: 2026-09-13 09:22:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/developer/how-to-watch-keys/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/developer/how-to-watch-keys/>

---

## Prerequisites

Install
etcd
and
etcdctl

etcd

etcdctl

## Watching keys

watch
to get notified of future changes:

watch

```
etcdctl watch
$KEY
[
$END_KEY
]
```

### Options

```
-i, --interactive
[=
false
]
: interactive mode
--prefix
[=
false
]
: watch on a prefix
if
prefix is
set
--rev
=
0: Revision to start watching
--prev-kv
[=
false
]
: get the previous key-value pair before the event happens
--progress-notify
[=
false
]
: get periodic watch progress notification from server
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
watch stock1
etcdctl --endpoints
=
$ENDPOINTS
put stock1
1000
etcdctl --endpoints
=
$ENDPOINTS
watch stock --prefix
etcdctl --endpoints
=
$ENDPOINTS
put stock1
10
etcdctl --endpoints
=
$ENDPOINTS
put stock2
20
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

> 完整与最新内容以官方文档为准：[How to watch keys](https://etcd.io/docs/v3.7/tasks/developer/how-to-watch-keys/)
