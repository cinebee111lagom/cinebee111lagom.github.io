---
title: etcd v3.7 抓取：Writing to etcd
date: 2026-09-13 09:18:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/developer/writing-to-etcd/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/developer/writing-to-etcd/>

---

## Prerequisites

Install
etcdctl

etcdctl

## Procedure

Use the
put
subcommand to write a key-value pair:

put

```
etcdctl --endpoints
=
$ENDPOINTS
put foo
"Hello World!"
```

where:

foo
is the key name

foo

"Hello World!"
is the quote-delimited value

"Hello World!"

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Writing to etcd](https://etcd.io/docs/v3.7/tasks/developer/writing-to-etcd/)
