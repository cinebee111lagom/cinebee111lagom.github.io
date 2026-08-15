---
title: Dragonfly 抓取：Deployment Best Practices
date: 2026-09-14 09:16:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/deployment/deployment-best-practices/>

---

Documentation for setting capacity planning and performance tuning for Dragonfly.

## Capacity Planning

A big factor in planning capacity is: highest expected storage capacity.
And know the memory size, CPU core count, and disk capacity of each machine.

For predicting your capacity, you can use the estimates from below if you don't have your capacity plan.

### Manager

The resources required to deploy the Manager depends on the total number of peers.

Run a minimum of 3 replicas.

### Scheduler

The resources required to deploy the Scheduler depends on the request per second.

Run a minimum of 3 replicas.

### Client

The resources required to deploy the Client depends on the request per second.

If it is a Seed Peer, run a minimum of 3 replicas. Disk are calculated based on file storage capacity.

### Cluster

The resources required to deploy each service in a P2P cluster depends on the total number of Peers.

## Performance tuning

The following documentation may help you to achieve better performance especially for large scale runs.

### Rate limits

#### Outbound Bandwidth

Used for node P2P to share piece bandwidth.
If the peak bandwidth is greater than the default outbound bandwidth,
you can set
bandwidthLimit
higher to increase the upload speed.
It is recommended that the configuration be the same as the inbound bandwidth of the machine.
Please refer to
dfdaemon config
.

```
upload
:
# -- bandwidthLimit is the default bandwidth limit of the upload speed in KB/MB/GB per second, default is 50GB/s.
bandwidthLimit
:
50GB
```

#### Inbound Bandwidth

Used for node back-to-source bandwidth and download bandwidth from remote peer.
If the peak bandwidth is greater than the default inbound bandwidth,
bandwidthLimit
can be set higher to increase download speed.
It is recommended that the configuration be the same as the outbound bandwidth of the machine.
Please refer to
dfdaemon config
.

```
download
:
# -- bandwidthLimit is the default bandwidth limit of the download speed in KB/MB/GB per second, default is 50GB/s.
bandwidthLimit
:
50GB
```

### Concurrency control

When used to download a single task of a node
the number of concurrent downloads of piece back-to-source and the number of concurrent downloads of piece from remote peer.
The larger the number of piece concurrency, the faster the task download, and the more CPU and memory will be consumed.
The user adjusts the number of piece concurrency according to the actual situation.
and adjust the client's CPU and memory configuration.
Please refer to
dfdaemon config
.

```
download
:
# -- concurrentPieceCount is the number of concurrent pieces to download.
concurrentPieceCount
:
10
```

### GC

Used for task cache GC in node disk, taskTTL is calculated based on cache time.
To avoid cases where GC would be problematic or potentially catastrophic,
it is recommended to use the default value.
Please refer to
dfdaemon config
.

```
gc
:
# interval is the interval to do gc.
interval
:
900s
policy
:
# taskTTL is the ttl of the task.
taskTTL
:
21600s
# distHighThresholdPercent is the high threshold percent of the disk usage.
# If the disk usage is greater than the threshold, dfdaemon will do gc.
distHighThresholdPercent
:
80
# distLowThresholdPercent is the low threshold percent of the disk usage.
# If the disk usage is less than the threshold, dfdaemon will stop gc.
distLowThresholdPercent
:
60
```

---

> 完整与最新内容以官方文档为准：[Deployment Best Practices](https://d7y.io/docs/next/operations/deployment/deployment-best-practices/)
