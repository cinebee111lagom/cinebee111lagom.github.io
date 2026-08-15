---
title: etcd v3.7 抓取：How to conduct leader election in etcd cluster
date: 2026-09-13 09:12:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/operator/how-to-conduct-elections/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/operator/how-to-conduct-elections/>

---

## Prerequisites

Ensure
etcd
and
etcdctl
is installed.

etcd

etcdctl

Check for active etcd cluster.

## Conduct Leader election

The
etcdctl
command is used to conduct leader elections in an etcd cluster. It makes sure that only one client can become leader at a time.

etcdctl

etcdctl --endpoints=$ENDPOINTS elect <election-name> [proposal]

```
etcdctl --endpoints
=
$ENDPOINTS
elect election-name p1
```

### Options

--endpoints : $ENDPOINTS

Address of each etcd cluster members.

election-name
string

election-name

A string identifier for the election. All participants competing for leadership must use the same election name.

leader-name
string

leader-name

Proposal value of the new leader.

### Example

```
./etcdctl elect my-election proposal1
my-election/694d99fafea88404
proposal1
another election:
./etcdctl elect new-election proposal1
new-election/694d99fafea8840f
proposal1
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

> 完整与最新内容以官方文档为准：[How to conduct leader election in etcd cluster](https://etcd.io/docs/v3.7/tasks/operator/how-to-conduct-elections/)
