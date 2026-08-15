---
title: etcd v3.7 抓取：Quickstart
date: 2026-09-13 09:01:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/quickstart/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/quickstart/>

---

Follow these instructions to locally install, run, and test a single-member
cluster of etcd:

Install etcd from pre-built binaries or from source. For details, see
Install
.
Important
: Ensure that you perform the last
step of the installation instructions to verify that
etcd
is in your path.

Install etcd from pre-built binaries or from source. For details, see
Install
.

Important
: Ensure that you perform the last
step of the installation instructions to verify that
etcd
is in your path.

etcd

Launch
etcd
:
$
etcd
{"level":"info","ts":"2021-09-17T09:19:32.783-0400","caller":"etcdmain/etcd.go:72","msg":... }
⋮
Note
: The output produced by
etcd
are
logs
— info-level logs can
be ignored.

Launch
etcd
:

etcd

```
$
etcd
{"level":"info","ts":"2021-09-17T09:19:32.783-0400","caller":"etcdmain/etcd.go:72","msg":... }
⋮
```

Note
: The output produced by
etcd
are
logs
— info-level logs can
be ignored.

etcd

From
another terminal
, use
etcdctl
to set a key:
$
etcdctl put greeting
"Hello, etcd"
OK

From
another terminal
, use
etcdctl
to set a key:

etcdctl

```
$
etcdctl put greeting
"Hello, etcd"
OK
```

From the same terminal, retrieve the key:
$
etcdctl get greeting
greeting
Hello, etcd

From the same terminal, retrieve the key:

```
$
etcdctl get greeting
greeting
Hello, etcd
```

## What’s next?

Learn about more ways to configure and use etcd from the following pages:

If you are a developer:
Explore the gRPC
API
.
Find
language bindings and tools
.

If you are a developer:

Explore the gRPC
API
.

Find
language bindings and tools
.

If you are an operator or admin:
Set up a
multi-machine cluster
.
Learn how to
configure
etcd.
Use TLS to
secure an etcd cluster
.
Tune etcd
.

If you are an operator or admin:

Set up a
multi-machine cluster
.

Learn how to
configure
etcd.

Use TLS to
secure an etcd cluster
.

Tune etcd
.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Quickstart](https://etcd.io/docs/v3.7/quickstart/)
