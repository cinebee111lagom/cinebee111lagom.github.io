---
title: etcd v3.7 抓取：How to get keys by prefix
date: 2026-09-13 09:19:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/developer/how-to-get-key-by-prefix/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/developer/how-to-get-key-by-prefix/>

---

## Pre-requisites

Install etcdctl

Setup a local cluster

## Get keys by prefix

```
$ etcdctl --endpoints
=
$ENDPOINTS
get PREFIX --prefix
```

### Global Options

```
--endpoints
=[
127.0.0.1:2379
]
, gRPC endpoints
```

### Options

```
--prefix, get a range of keys with matching prefix
```

### Example

```
etcdctl --endpoints
=
$ENDPOINTS
put web1 value1
etcdctl --endpoints
=
$ENDPOINTS
put web2 value2
etcdctl --endpoints
=
$ENDPOINTS
put web3 value3
etcdctl --endpoints
=
$ENDPOINTS
get web --prefix
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

> 完整与最新内容以官方文档为准：[How to get keys by prefix](https://etcd.io/docs/v3.7/tasks/developer/how-to-get-key-by-prefix/)
