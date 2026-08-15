---
title: etcd v3.7 抓取：Data Corruption
date: 2026-09-13 09:46:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/op-guide/data_corruption/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/op-guide/data_corruption/>

---

etcd has built in automated data corruption detection to prevent member state from diverging.

## Enabling data corruption detection

Data corruption detection can be done using:

Initial check, enabled with
--experimental-initial-corrupt-check
flag.

--experimental-initial-corrupt-check

Periodic check of:
Compacted revision hash, enabled with
--experimental-compact-hash-check-enabled
flag.
Latest revision hash, enabled with
--experimental-corrupt-check-time
flag.

Compacted revision hash, enabled with
--experimental-compact-hash-check-enabled
flag.

--experimental-compact-hash-check-enabled

Latest revision hash, enabled with
--experimental-corrupt-check-time
flag.

--experimental-corrupt-check-time

Initial check will be executed during bootstrap of etcd member.
Member will compare its persistent state vs other members and exit if there is a mismatch.

Both periodic check will be executed by the cluster leader in a cluster that is already running.
Leader will compare its persistent state vs other members and raise a CORRUPT ALARM if there is a mismatch.
Both checks serve the same purpose, however they are both worth enabling to balance performance and time to detection.

Compacted revision hash check - requires regular compaction, minimal performance cost, handles slow followers.

Latest revision hash check - high performance cost, doesn’t handle slow followers or frequent compactions.

### Compacted revision hash check

When enabled using
--experimental-compact-hash-check-enabled
flag, check will be executed once every minute.
This can be adjusted using
--experimental-compact-hash-check-time
flag using format:
1m
- every minute,
1h
- evey hour.
This check extends compaction to also calculate checksum that can be compared between cluster members.
Doesn’t cause additional database scan making it very cheap, but requiring a regular compaction in cluster.

--experimental-compact-hash-check-enabled

--experimental-compact-hash-check-time

1m

1h

### Latest revision hash check

Enabled using
--experimental-corrupt-check-time
flag, requires providing an execution period in format:
1m
- every minute,
1h
- evey hour.
Recommended period is a couple of hours due to a high performance cost.
Running a check requires computing a checksum by scanning entire etcd content at given revision.

--experimental-corrupt-check-time

1m

1h

## Restoring a corrupted member

There are three ways to restore a corrupted member:

Purge member persistent state

Replace member

Restore whole cluster

After the corrupted member is restored, CORRUPT ALARM can be removed.

### Purge member persistent state

Members state can be purged by:

Stopping the etcd instance.

Backing up etcd data directory.

Moving out the
snap
subdirectory from the etcd data directory.

snap

Starting
etcd
with
--initial-cluster-state=existing
and cluster members listed in
--initial-cluster
.

etcd

--initial-cluster-state=existing

--initial-cluster

Etcd member is expected to download up-to-date snapshot from the leader.

### Replace member

Member can be replaced by:

Stopping the etcd instance.

Backing up the etcd data directory.

Removing the data directory.

Removing the member from cluster by running
etcdctl member remove
.

etcdctl member remove

Adding it back by running
etcdctl member add

etcdctl member add

Starting
etcd
with
--initial-cluster-state=existing
and cluster members listed in
--initial-cluster
.

etcd

--initial-cluster-state=existing

--initial-cluster

### Restore whole cluster

Cluster can be restored by saving a snapshot from current leader and restoring it to all members.
Run
etcdctl snapshot save
against the leader and follow
restoring a cluster procedure
.

etcdctl snapshot save

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Data Corruption](https://etcd.io/docs/v3.7/op-guide/data_corruption/)
