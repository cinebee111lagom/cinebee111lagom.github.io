---
title: etcd v3.7 抓取：Versioning
date: 2026-09-13 09:45:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/op-guide/versioning/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/op-guide/versioning/>

---

This document describes the versions supported by the etcd project.

## Service versioning and supported versions

etcd versions are expressed as
x.y.z
, where
x
is the major version,
y
is the minor version, and
z
is the patch version, following
Semantic Versioning
terminology.
New minor versions may add additional features to the API.

The etcd project maintains release branches for the current version and previous release. For example, when v3.5 is the current version, v3.4 is supported. When v3.6 is released, v3.4 goes out of support.

Applicable fixes, including security fixes, may be backported to those two release branches, depending on severity and feasibility.
Patch releases are cut from those branches when required.

The project
Maintainers
own this decision.

You can check the running etcd cluster version with
etcdctl
:

etcdctl

```
etcdctl --endpoints
=
127.0.0.1:2379 endpoint status
```

## API versioning

The
v3
API responses should not change after the 3.0.0 release but new features will be added over time.

v3

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Versioning](https://etcd.io/docs/v3.7/op-guide/versioning/)
