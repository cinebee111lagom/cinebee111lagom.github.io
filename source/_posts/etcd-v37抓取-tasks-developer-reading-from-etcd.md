---
title: etcd v3.7 抓取：Reading from etcd
date: 2026-09-13 09:17:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/developer/reading-from-etcd/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/developer/reading-from-etcd/>

---

## Prerequisites

Install
etcdctl

etcdctl

## Procedure

Use the
get
subcommand to read from etcd:

get

```
$ etcdctl --endpoints
=
$ENDPOINTS
get foo
foo
Hello World!
$
```

where:

foo
is the requested key

foo

Hello World!
is the retrieved value

Hello World!

Or, for formatted output:

```
$ etcdctl --endpoints=$ENDPOINTS --write-out="json" get foo
{"header":{"cluster_id":289318470931837780,"member_id":14947050114012957595,"revision":3,"raft_term":4,
"kvs":[{"key":"Zm9v","create_revision":2,"mod_revision":3,"version":2,"value":"SGVsbG8gV29ybGQh"}]}}
$
```

where
write-out="json"
causes the value to be output in JSON format (note that the key is not returned).

write-out="json"

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Reading from etcd](https://etcd.io/docs/v3.7/tasks/developer/reading-from-etcd/)
