---
title: etcd v3.7 抓取：Upgrade etcd from v3.5 to v3.6
date: 2026-09-13 10:16:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/upgrades/upgrade_3_6/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/upgrades/upgrade_3_6/>

---

In the general case, upgrading from etcd v3.5 to v3.6 can be a zero-downtime, rolling upgrade:

one by one, stop the etcd v3.5 processes and replace them with etcd v3.6 processes

after running all v3.6 processes, new features in v3.6 are available to the cluster

Before
starting an upgrade
, read through the rest of this guide to prepare.

### Upgrade checklists

#### Update 3.5

Before upgrading to 3.6, make sure that
all of your 3.5 members are updated to 3.5.32 or later
. Patch releases 3.5.24 through 3.5.26 fix several potential upgrade blockers;
3.5.32
adds
--v2-deprecation=write-only-skip-check
and extends
etcdutl check v2store
to inspect WAL records as well as the v2 snapshot.

--v2-deprecation=write-only-skip-check

etcdutl check v2store

#### V2 Store

If the
--enable-v2
flag is not configured or is set to false, no further action is required.

--enable-v2

If
--enable-v2
is
configured, run the command
etcdutl check v2store
to verify whether the v2store contains any non-membership (custom) data. If no custom data is present, the flag can be safely removed. Otherwise, refer to the
v2 migration guide
for more details.

--enable-v2

etcdutl check v2store

### Flags added

```
+etcd --discovery-token ''
+etcd --discovery-endpoints ''
+etcd --discovery-dial-timeout '2s'
+etcd --discovery-request-timeout '5s'
+etcd --discovery-keepalive-time '2s'
+etcd --discovery-keepalive-timeout '6s'
+etcd --discovery-insecure-transport 'true'
+etcd --discovery-insecure-skip-tls-verify 'false'
+etcd --discovery-cert ''
+etcd --discovery-key ''
+etcd --discovery-cacert ''
+etcd --discovery-user ''
+etcd --discovery-password ''
+etcd --feature-gates
+etcd --log-format
```

### Flags removed

```
-etcd --enable-v2
-etcd --experimental-enable-v2v3
-etcd --proxy
-etcd --proxy-failure-wait
-etcd --proxy-refresh-interval
-etcd --proxy-dial-timeout
-etcd --proxy-write-timeout
-etcd --proxy-read-timeout
```

### Flags deprecated

etcd --experimental-bootstrap-defrag-threshold-megabytes
flag has been deprecated.

etcd --experimental-bootstrap-defrag-threshold-megabytes

```
-etcd --experimental-bootstrap-defrag-threshold-megabytes
+etcd --bootstrap-defrag-threshold-megabytes
```

etcd --experimental-compaction-batch-limit
flag has been deprecated.

etcd --experimental-compaction-batch-limit

```
-etcd --experimental-compaction-batch-limit
+etcd --compaction-batch-limit
```

etcd --experimental-compact-hash-check-time
flag has been deprecated.

etcd --experimental-compact-hash-check-time

```
-etcd --experimental-compact-hash-check-time
+etcd --compact-hash-check-time
```

etcd --experimental-compaction-sleep-interval
flag has been deprecated.

etcd --experimental-compaction-sleep-interval

```
-etcd --experimental-compaction-sleep-interval
+etcd --compaction-sleep-interval
```

etcd --experimental-corrupt-check-time
flag has been deprecated.

etcd --experimental-corrupt-check-time

```
-etcd --experimental-corrupt-check-time
+etcd --corrupt-check-time
```

etcd --experimental-enable-distributed-tracing
flag has been deprecated.

etcd --experimental-enable-distributed-tracing

```
-etcd --experimental-enable-distributed-tracing
+etcd --enable-distributed-tracing
```

etcd --experimental-distributed-tracing-address
flag has been deprecated.

etcd --experimental-distributed-tracing-address

```
-etcd --experimental-distributed-tracing-address
+etcd --distributed-tracing-address
```

etcd --experimental-distributed-tracing-instance-id
flag has been deprecated.

etcd --experimental-distributed-tracing-instance-id

```
-etcd --experimental-distributed-tracing-instance-id
+etcd --distributed-tracing-instance-id
```

etcd --experimental-distributed-tracing-sampling-rate
flag has been deprecated.

etcd --experimental-distributed-tracing-sampling-rate

```
-etcd --experimental-distributed-tracing-sampling-rate
+etcd --distributed-tracing-sampling-rate
```

etcd --experimental-distributed-tracing-service-name
flag has been deprecated.

etcd --experimental-distributed-tracing-service-name

```
-etcd --experimental-distributed-tracing-service-name
+etcd --distributed-tracing-service-name
```

etcd --experimental-downgrade-check-time
flag has been deprecated.

etcd --experimental-downgrade-check-time

```
-etcd --experimental-downgrade-check-time
+etcd --downgrade-check-time
```

etcd --experimental-max-learners
flag has been deprecated.

etcd --experimental-max-learners

```
-etcd --experimental-max-learners
+etcd --max-learners
```

etcd --experimental-memory-mlock
flag has been deprecated.

etcd --experimental-memory-mlock

```
-etcd --experimental-memory-mlock
+etcd --memory-mlock
```

etcd --experimental-peer-skip-client-san-verification
flag has been deprecated.

etcd --experimental-peer-skip-client-san-verification

```
-etcd --experimental-peer-skip-client-san-verification
+etcd --peer-skip-client-san-verification
```

etcd --experimental-snapshot-catchup-entries
flag has been deprecated.

etcd --experimental-snapshot-catchup-entries

```
-etcd --experimental-snapshot-catchup-entries
+etcd --snapshot-catchup-entries
```

etcd --experimental-warning-apply-duration
flag has been deprecated.

etcd --experimental-warning-apply-duration

```
-etcd --experimental-warning-apply-duration
+etcd --warning-apply-duration
```

etcd --experimental-warning-unary-request-duration
flag has been deprecated.

etcd --experimental-warning-unary-request-duration

```
-etcd --experimental-warning-unary-request-duration
+etcd --warning-unary-request-duration
```

etcd --experimental-watch-progress-notify-interval
flag has been deprecated.

etcd --experimental-watch-progress-notify-interval

```
-etcd --experimental-watch-progress-notify-interval
+etcd --watch-progress-notify-interval
```

### Equivalent flags of v3.5 feature gates

equivalent flag for feature gate
etcd --experimental-compact-hash-check-enabled=true

etcd --experimental-compact-hash-check-enabled=true

```
-etcd --experimental-compact-hash-check-enabled=true
+etcd --feature-gates=CompactHashCheck=true
```

equivalent flag for feature gate
etcd --experimental-initial-corrupt-check=true

etcd --experimental-initial-corrupt-check=true

```
-etcd --experimental-initial-corrupt-check=true
+etcd --feature-gates=InitialCorruptCheck=true
```

equivalent flag for feature gate
etcd --experimental-enable-lease-checkpoint=true

etcd --experimental-enable-lease-checkpoint=true

```
-etcd --experimental-enable-lease-checkpoint=true
+etcd --feature-gates=LeaseCheckpoint=true
```

equivalent flag for feature gate
etcd --experimental-enable-lease-checkpoint-persist=true

etcd --experimental-enable-lease-checkpoint-persist=true

```
-etcd --experimental-enable-lease-checkpoint-persist=true
+etcd --feature-gates=LeaseCheckpointPersist=true
```

equivalent flag for feature gate
etcd --experimental-stop-grpc-service-on-defrag=true

etcd --experimental-stop-grpc-service-on-defrag=true

```
-etcd --experimental-stop-grpc-service-on-defrag=true
+etcd --feature-gates=StopGRPCServiceOnDefrag=true
```

equivalent flag for feature gate
etcd --experimental-txn-mode-write-with-shared-buffer=false

etcd --experimental-txn-mode-write-with-shared-buffer=false

```
-etcd --experimental-txn-mode-write-with-shared-buffer=false
+etcd --feature-gates=TxnModeWriteWithSharedBuffer=false
```

### Flags with new defaults

Original default flag
etcd --snapshot-count=100000

etcd --snapshot-count=100000

```
-etcd --snapshot-count=100000
+etcd --snapshot-count=10000
```

Original default flag
etcd --v2-deprecation='not-yet'

etcd --v2-deprecation='not-yet'

```
-etcd --v2-deprecation='not-yet'
+etcd --v2-deprecation='write-only'
```

Original default flag
etcd --discovery-fallback='proxy'

etcd --discovery-fallback='proxy'

```
-etcd --discovery-fallback='proxy'
+etcd --discovery-fallback='exit'
```

### Difference in Prometheus metrics

```
# metrics added in v3.6
+etcd_network_known_peers
+etcd_server_feature_enabled
```

### Server upgrade checklists

#### Upgrade requirements

To upgrade an existing etcd deployment to v3.6, the running cluster must be v3.5 or greater. If it’s before v3.5, please
upgrade to v3.5
before upgrading to v3.6.

Also, to ensure a smooth rolling upgrade, the running cluster must be healthy. Check the health of the cluster by using the
etcdctl endpoint health
command before proceeding.

etcdctl endpoint health

#### Preparation

Before upgrading etcd, always test the services relying on etcd in a staging environment before deploying the upgrade to the production environment.

Before beginning,
download the snapshot backup
. Should something go wrong with the upgrade, it is possible to use this backup to
rollback
back to existing etcd version. Please note that the
snapshot
command only backs up the v3 data.

snapshot

#### Mixed versions

While upgrading, an etcd cluster supports mixed versions of etcd members, and operates with the protocol of the lowest common version. The cluster is only considered upgraded once all of its members are upgraded to version v3.6. Internally, etcd members negotiate with each other to determine the overall cluster version, which controls the reported version and the supported features.

#### Rollback

Before upgrading your etcd cluster, please create and
download a snapshot backup
of your etcd cluster. This snapshot can be used to restore the cluster to its pre-upgrade state if needed. If users encounter issues during the upgrade, they should first identify and resolve the root cause. If the cluster is still in a mixed-version state—where at least one member remains on v3.5—they can either replace the binary or image with the old v3.5 version or restore the cluster directly using the snapshot. In this mixed state, the cluster continues to operate as a v3.5 cluster, allowing rollback without following a formal downgrade process.

However, once all members have been upgraded to v3.6, the cluster is considered fully upgraded and rollback using binaries is no longer possible. In that case, the only recovery option is to restore from the snapshot taken before the upgrade. If users wish to return to the original version after a full upgrade has completed, they should follow the official downgrade guide to ensure consistency and avoid data corruption.

### Upgrade procedure

This example shows how to upgrade a 3-member v3.5 etcd cluster running on a local machine.

#### Step 1: check upgrade requirements

Is the cluster healthy and running v3.5.x?

```
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint health
<<COMMENT
localhost:2379 is healthy: successfully committed proposal: took = 2.555774ms
localhost:32379 is healthy: successfully committed proposal: took = 2.631133ms
localhost:22379 is healthy: successfully committed proposal: took = 3.020958ms
COMMENT
curl http://localhost:2379/version
<<COMMENT
{"etcdserver":"3.5.18","etcdcluster":"3.5.0"}
COMMENT
curl http://localhost:22379/version
<<COMMENT
{"etcdserver":"3.5.18","etcdcluster":"3.5.0"}
COMMENT
curl http://localhost:32379/version
<<COMMENT
{"etcdserver":"3.5.18","etcdcluster":"3.5.0"}
COMMENT
```

#### Step 2: download snapshot backup from leader

Download the snapshot backup
to provide a downgrade path should any problems occur.

etcd leader is guaranteed to have the latest application data, thus fetch snapshot from leader:


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Upgrade etcd from v3.5 to v3.6](https://etcd.io/docs/v3.7/upgrades/upgrade_3_6/)
