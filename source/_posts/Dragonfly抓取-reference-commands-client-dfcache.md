---
title: Dragonfly 抓取：Dfcache
date: 2026-09-14 10:00:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/reference/commands/client/dfcache/>

---

dfcache
is the command-line tool of dragonfly that communicates with dfdaemon and operates on files in P2P network,
and it can copy multiple replicas during import. P2P cache is effectively used for fast read and write cache.

## Usage

Import a file into Dragonfly P2P network.

```
dfcache import <PATH>
```

Export a file from Dragonfly P2P network.

```
dfcache export <ID> -O <OUTPUT> <PATH>
```

Get file information in Dragonfly P2P network.

```
dfcache stat <ID>
```

## Example

### Import

```
dfcache import /tmp/file.txt
```

#### Configuring persistent replicas and TTL

Use the following parameters to specify the number of replicas and ttl of the persistent cache task.

```
dfcache import --persistent-replica-count 3 --ttl 2h /tmp/file.txt
```

#### Importing large file

The default ID is calculated based on the file's SHA256. For large files,
this process may take longer. You can specify
--content-for-calculating-task-id
to define the file's uniqueness.
For example,
--content-for-calculating-task-id
can be set to the filename, provided it ensures uniqueness.

```
dfcache import --content-for-calculating-task-id <CONTENT_FOR_CALCULATING_TASK_ID> /tmp/file.txt
```

### Export

```
dfcache export <ID> -O /tmp/file.txt
```

#### Export in Container

Deploy Dragonfly components across your cluster:

```
helm repo add dragonfly https://dragonflyoss.github.io/helm-charts/
helm install --create-namespace -n dragonfly-system dragonfly dragonfly/dragonfly
```

For detailed installation options, refer to
Helm Charts Installation Guide
.

Add the following configuration to your Pod definition to mount the Dragonfly daemon's Unix Domain Socket,
then the container can use the same dfdaemon to export files in the node.

```
apiVersion
:
v1
kind
:
Pod
metadata
:
name
:
runtime
spec
:
containers
:
-
name
:
runtime
image
:
your
-
image
:
tag
volumeMounts
:
-
mountPath
:
/var/run/dragonfly
name
:
dfdaemon
-
socket
-
dir
volumes
:
-
name
:
dfdaemon
-
socket
-
dir
hostPath
:
path
:
/var/run/dragonfly
type
:
DirectoryOrCreate
```

Install dfcache in the Container Image, refer to
Install Client using RPM
or
Install Client using DEB
.

Once set up, use the dfcache command with the
--transfer-from-dfdaemon
flag to export files:

```
dfcache export --transfer-from-dfdaemon <ID> -O /tmp/file.txt
```

### Stat

```
dfcache stat <ID>
```

## Log

```
1. set option --console if you want to print logs to Terminal
2. log path: /var/log/dragonfly/dfcache/
```

---

> 完整与最新内容以官方文档为准：[Dfcache](https://d7y.io/docs/next/reference/commands/client/dfcache/)
