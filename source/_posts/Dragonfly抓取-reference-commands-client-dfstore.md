---
title: Dragonfly 抓取：Dfstore
date: 2026-09-14 10:02:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/reference/commands/client/dfstore/>

---

dfstore
is a storage command line based on P2P technology in Dragonfly that can import file and export file
in P2P network, and it can create multiple replicas on different peers and provides persistence by copying
data to object storage. P2P cache is effectively used for fast read and write cache.

## Usage

Import a local file into Dragonfly P2P network and create multiple replicas on different peers
and provides persistence by copying data to object storage.

```
dfstore import <PATH> --url <URL>
```

Export a file from Dragonfly P2P network. If export successfully, it will return the local file path.

```
dfstore export <URL> --output <OUTPUT>
```

The
--url
is the URL for copying data to object storage, the format is
scheme://<bucket>/<path>
,
such as
s3://<bucket>/<path>
for Amazon Simple Storage Service(S3) and
abs://<bucket>/<path>
for Azure Blob Storage(ABS).

## Example

### Import

Import a file into Dragonfly P2P network and persist it to object storage:

```
$ dfstore import /tmp/file.txt --url s3://<bucket>/<path> --storage-region <REGION> --storage-access-key-id <ACCESS_KEY_ID> --storage-access-key-secret <ACCESS_KEY_SECRET>
⣷ Done: s3://<bucket>/<path>
```

#### Configuring persistent replicas and TTL

Use the following parameters to specify the number of replicas and ttl of the persistent task.

```
dfstore import --persistent-replica-count 3 --ttl 2h /tmp/file.txt --url s3://<bucket>/<path>
```

### Export

```
$ dfstore export s3://<bucket>/<path> --output /tmp/file.txt --storage-region <REGION> --storage-access-key-id <ACCESS_KEY_ID> --storage-access-key-secret <ACCESS_KEY_SECRET>
[00:00:00] [############################################################] 8.73 KiB/8.73 KiB (7.30 MiB/s, 0.0s)
```

If the container shares the dfdaemon of the node via the unix domain socket, use the
--transfer-from-dfdaemon
flag to transfer the content of the file from dfdaemon,
refer to
Export in Container
.

```
dfstore export --transfer-from-dfdaemon s3://<bucket>/<path> --output /tmp/file.txt
```

## Log

```
1. set option --console if you want to print logs to Terminal
2. log path: /var/log/dragonfly/dfstore/
```

---

> 完整与最新内容以官方文档为准：[Dfstore](https://d7y.io/docs/next/reference/commands/client/dfstore/)
