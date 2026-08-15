---
title: Dragonfly 抓取：Persistent Task
date: 2026-09-14 09:09:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/concepts/persistent-task/>

---

It designs to provide persistent storage for tasks. A persistent task is imported into the P2P network
with multiple replicas on different peers, and provides persistence by copying the data to object storage.
The P2P cache is effectively used for fast read and write operations, and the object storage serves as the
persistent backend. This makes it particularly advantageous for scenarios involving large files, such as
machine learning model checkpoints, where rapid, reliable access and distribution across the network are
critical for training and inference workflows.

The persistent task metadata is stored in Redis of the scheduler, so it is only available when the
scheduler is deployed with Redis, refer to
Deployment Models
.

## Dfstore

Use dfstore to import a local file into the P2P network, create replicas on different peers and
persist the data to object storage, please refer to
dfstore
.

```
$ dfstore import /tmp/file.txt --url s3://<bucket>/<path>
⣷ Done: s3://<bucket>/<path>
```

Use dfstore to export a file from the P2P network:

```
$ dfstore export s3://<bucket>/<path> --output /tmp/file.txt
[00:00:00] [############################################################] 8.73 KiB/8.73 KiB (7.30 MiB/s, 0.0s)
```

## Dfctl

List all persistent tasks in client's local storage, please refer to
dfctl
.

```
dfctl persistent-task ls
```

---

> 完整与最新内容以官方文档为准：[Persistent Task](https://d7y.io/docs/next/concepts/persistent-task/)
