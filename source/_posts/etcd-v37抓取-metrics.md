---
title: etcd v3.7 抓取：Metrics
date: 2026-09-13 10:31:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/metrics/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/metrics/>

---

etcd uses
Prometheus
for metrics reporting. The metrics can be used for real-time monitoring and debugging. etcd does not persist its metrics; if a member restarts, the metrics will be reset.

The simplest way to see the available metrics is to cURL the metrics endpoint
/metrics
. The format is described
in the Prometheus docs
.

/metrics

Follow the
Prometheus getting started doc
to spin up a Prometheus server to collect etcd metrics.

The naming of metrics follows the suggested
Prometheus best practices
. A metric name has an
etcd
or
etcd_debugging
prefix as its namespace and a subsystem prefix (for example
wal
and
etcdserver
).

etcd

etcd_debugging

wal

etcdserver

## etcd namespace metrics

The metrics under the
etcd
prefix are for monitoring and alerting. They are stable high level metrics. If there is any change of these metrics, it will be included in release notes.

etcd

Metrics that are etcd2 related are documented in the
v2 metrics guide
.

### Server

These metrics describe the status of the etcd server. In order to detect outages or problems for troubleshooting, the server metrics of every production etcd cluster should be closely monitored.

All these metrics are prefixed with
etcd_server_

etcd_server_

has_leader
indicates whether the member has a leader. If a member does not have a leader, it is
totally unavailable. If all the members in the cluster do not have any leader, the entire cluster
is totally unavailable.

has_leader

leader_changes_seen_total
counts the number of leader changes the member has seen since its start. Rapid leadership changes impact the performance of etcd significantly. It also signals that the leader is unstable, perhaps due to network connectivity issues or excessive load hitting the etcd cluster.

leader_changes_seen_total

proposals_committed_total
records the total number of consensus proposals committed. This gauge should increase over time if the cluster is healthy. Several healthy members of an etcd cluster may have different total committed proposals at once. This discrepancy may be due to recovering from peers after starting, lagging behind the leader, or being the leader and therefore having the most commits. It is important to monitor this metric across all the members in the cluster; a consistently large lag between a single member and its leader indicates that member is slow or unhealthy.

proposals_committed_total

proposals_applied_total
records the total number of consensus proposals applied. The etcd server applies every committed proposal asynchronously. The difference between
proposals_committed_total
and
proposals_applied_total
should usually be small (within a few thousands even under high load). If the difference between them continues to rise, it indicates that the etcd server is overloaded. This might happen when applying expensive queries like heavy range queries or large txn operations.

proposals_applied_total

proposals_committed_total

proposals_applied_total

proposals_pending
indicates how many proposals are queued to commit. Rising pending proposals suggests there is a high client load or the member cannot commit proposals.

proposals_pending

proposals_failed_total
are normally related to two issues: temporary failures related to a leader election or longer downtime caused by a loss of quorum in the cluster.

proposals_failed_total

### Disk

These metrics describe the status of the disk operations.

All these metrics are prefixed with
etcd_disk_
.

etcd_disk_

A
wal_fsync
is called when etcd persists its log entries to disk before applying them.

wal_fsync

A
backend_commit
is called when etcd commits an incremental snapshot of its most recent changes to disk.

backend_commit

High disk operation latencies (
wal_fsync_duration_seconds
or
backend_commit_duration_seconds
) often indicate disk issues. It may cause high request latency or make the cluster unstable.

wal_fsync_duration_seconds

backend_commit_duration_seconds

### Network

These metrics describe the status of the network.

All these metrics are prefixed with
etcd_network_

etcd_network_

To

From

To

From

peer_sent_bytes_total
counts the total number of bytes sent to a specific peer. Usually the leader member sends more data than other members since it is responsible for transmitting replicated data.

peer_sent_bytes_total

peer_received_bytes_total
counts the total number of bytes received from a specific peer. Usually follower members receive data only from the leader member.

peer_received_bytes_total

### gRPC requests

These metrics are exposed via
go-grpc-prometheus
.

## etcd_debugging namespace metrics

The metrics under the
etcd_debugging
prefix are for debugging. They are very implementation dependent and volatile. They might be changed or removed without any warning in new etcd releases. Some of the metrics might be moved to the
etcd
prefix when they become more stable.

etcd_debugging

etcd

### Snapshot

Abnormally high snapshot duration (
snapshot_save_total_duration_seconds
) indicates disk issues and might cause the cluster to be unstable.

snapshot_save_total_duration_seconds

## Prometheus supplied metrics

The Prometheus client library provides a number of metrics under the
go
and
process
namespaces. There are a few that are particularly interesting.

go

process

The process metrics, such as
process_open_fds
and
process_max_fds
, are not supported on Darwin (macOS) systems at this time.

process_open_fds

process_max_fds

Heavy file descriptor (
process_open_fds
) usage (i.e., near the process’s file descriptor limit,
process_max_fds
) indicates a potential file descriptor exhaustion issue. If the file descriptors are exhausted, etcd may panic because it cannot create new WAL files.

process_open_fds

process_max_fds

## Generated list of metrics

latest

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Metrics](https://etcd.io/docs/v3.7/metrics/)
