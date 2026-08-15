---
title: Dragonfly 抓取：Preheat
date: 2026-09-14 09:39:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/preheat/>

---

Preheating downloads files or images to the seed peers or peers ahead of time,
so that the following downloads hit the cache of the P2P cluster directly.

Dragonfly provides different ways to preheat depending on the deployment model,
refer to
Deployment Models
:

Without Manager
: use
dfctl
to preheat, which calls the scheduler gRPC directly.

With Manager
: use the Open API or the web console to preheat.

## Preheat via dfctl

In the lightweight deployment (without the Manager), use
dfctl task preheat
to preheat.
It calls the scheduler gRPC directly and triggers the seed peers or peers to download the
task, refer to
dfctl
.

Preheat a file task:

```
dfctl task preheat https://example.com/file.txt --scheduler-endpoint http://scheduler-service:8002
```

Preheat an image task:

```
dfctl task preheat oci://docker.io/library/alpine:3.19 --scheduler-endpoint http://scheduler-service:8002 --username <USERNAME> --password <PASSWORD>
```

The scope of preheating can be specified with the
--scope
flag:

single_seed_peer
: preheat to a single seed peer.

all_seed_peers
: preheat to all seed peers, default value. The
--ip
,
--count
and
--percentage
flags can limit the seed peers to preheat.

all_peers
: preheat to all peers. The
--ip
,
--count
and
--percentage
flags can
limit the peers to preheat.

Preheat an image task to all peers:

```
dfctl task preheat oci://docker.io/library/alpine:3.19 --scheduler-endpoint http://scheduler-service:8002 --scope all_peers
```

In kubernetes,
dfctl
is included in the client image, so you can preheat by executing
dfctl
in a client pod:

```
# Find pod name.
export POD_NAME=$(kubectl get pods --namespace dragonfly-system -l "app=dragonfly,release=dragonfly,component=client" -o jsonpath={.items[0].metadata.name})
# Preheat an image task.
kubectl -n dragonfly-system exec -it ${POD_NAME} -- dfctl task preheat oci://docker.io/library/alpine:3.19 --scheduler-endpoint http://dragonfly-scheduler.dragonfly-system.svc.cluster.local:8002
```

## Preheat via Open API

In the deployment with Manager, use the Open API to create a preheat job. The Manager
distributes the preheat job to the schedulers, and the schedulers trigger the seed peers
or peers to download the task, refer to
Open API preheat
.

## Preheat via web console

In the deployment with Manager, you can also create and manage preheat jobs in the
web console, refer to
web console preheat
.

---

> 完整与最新内容以官方文档为准：[Preheat](https://d7y.io/docs/next/advanced-guides/preheat/)
