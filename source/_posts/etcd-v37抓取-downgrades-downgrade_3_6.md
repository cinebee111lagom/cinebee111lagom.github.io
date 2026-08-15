---
title: etcd v3.7 抓取：Downgrade etcd from v3.6 to v3.5
date: 2026-09-13 10:21:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/downgrades/downgrade_3_6/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/downgrades/downgrade_3_6/>

---

In the general case, downgrading from etcd v3.6 to v3.5 can be a zero-downtime, rolling downgrade:

one by one, stop the etcd v3.6 processes and replace them with etcd v3.5 processes

after enabling the downgrade, new features in v3.6 are no longer available to the cluster

Before
starting a downgrade
, read through the rest of this guide to prepare.

### Downgrade checklists

Highlighted breaking changes from v3.6 to v3.5:

#### Difference in flags

If you are using any of the following flags in your v3.6 configurations, make sure to remove, rename, or change the default value when downgrading to v3.5.

The diff is based on version v3.6.0 and v.3.5.18. The actual diff would be dependent on your patch version, check with
diff <(etcd-3.6/bin/etcd -h | grep \\-\\-) <(etcd-3.5/bin/etcd -h | grep \\-\\-)
first.

diff <(etcd-3.6/bin/etcd -h | grep \\-\\-) <(etcd-3.5/bin/etcd -h | grep \\-\\-)

```
# flags not available in v3.5
-etcd --discovery-token ''
-etcd --discovery-endpoints ''
-etcd --discovery-dial-timeout '2s'
-etcd --discovery-request-timeout '5s'
-etcd --discovery-keepalive-time '2s'
-etcd --discovery-keepalive-timeout '6s'
-etcd --discovery-insecure-transport 'true'
-etcd --discovery-insecure-skip-tls-verify 'false'
-etcd --discovery-cert ''
-etcd --discovery-key ''
-etcd --discovery-cacert ''
-etcd --discovery-user ''
-etcd --discovery-password ''
-etcd --feature-gates
-etcd --log-format
# same flag with different names
-etcd --bootstrap-defrag-threshold-megabytes
+etcd --experimental-bootstrap-defrag-threshold-megabytes
-etcd --compaction-batch-limit
+etcd --experimental-compaction-batch-limit
-etcd --compact-hash-check-time
+etcd --experimental-compact-hash-check-time
-etcd --compaction-sleep-interval
+etcd --experimental-compaction-sleep-interval
-etcd --corrupt-check-time
+etcd --experimental-corrupt-check-time
-etcd --enable-distributed-tracing
+etcd --experimental-enable-distributed-tracing
-etcd --distributed-tracing-address
+etcd --experimental-distributed-tracing-address
-etcd --distributed-tracing-instance-id
+etcd --experimental-distributed-tracing-instance-id
-etcd --distributed-tracing-sampling-rate
+etcd --experimental-distributed-tracing-sampling-rate
-etcd --distributed-tracing-service-name
+etcd --experimental-distributed-tracing-service-name
-etcd --downgrade-check-time
+etcd --experimental-downgrade-check-time
-etcd --max-learners
+etcd --experimental-max-learners
-etcd --memory-mlock
+etcd --experimental-memory-mlock
-etcd --peer-skip-client-san-verification
+etcd --experimental-peer-skip-client-san-verification
-etcd --snapshot-catchup-entries
+etcd --experimental-snapshot-catchup-entries
-etcd --warning-apply-duration
+etcd --experimental-warning-apply-duration
-etcd --warning-unary-request-duration
+etcd --experimental-warning-unary-request-duration
-etcd --watch-progress-notify-interval
+etcd --experimental-watch-progress-notify-interval
# equivalent flags of v3.6 feature gates
-etcd --feature-gates=CompactHashCheck=true
+etcd --experimental-compact-hash-check-enabled=true
-etcd --feature-gates=InitialCorruptCheck=true
+etcd --experimental-enable-initial-corrupt-check=true
-etcd --feature-gates=LeaseCheckpoint=true
+etcd --experimental-enable-lease-checkpoint=true
-etcd --feature-gates=LeaseCheckpointPersist=true
+etcd --experimental-enable-lease-checkpoint-persist=true
-etcd --feature-gates=StopGRPCServiceOnDefrag=true
+etcd --experimental-stop-grpc-service-on-defrag=true
-etcd --feature-gates=TxnModeWriteWithSharedBuffer=false
+etcd --experimental-txn-mode-write-with-shared-buffer=false
# same flag different defaults
-etcd --snapshot-count=10000
+etcd --snapshot-count=100000
-etcd --v2-deprecation='write-only'
+etcd --v2-deprecation='not-yet'
-etcd --discovery-fallback='exit'
+etcd --discovery-fallback='proxy'
```

#### Difference in Prometheus metrics

```
# metrics not available in v3.5
-etcd_network_known_peers
-etcd_server_feature_enabled
```

### Server downgrade checklists

#### Downgrade requirements

To ensure a smooth rolling downgrade, the running cluster must be healthy. Check the health of the cluster by using the
etcdctl endpoint health
command before proceeding.

etcdctl endpoint health

#### Preparation

Before downgrading etcd, always test the services relying on etcd in a staging environment before deploying the downgrade to the production environment.

Before beginning,
download the snapshot backup
. Should something go wrong with the downgrade, it is possible to use this backup to
rollback
back to existing etcd version.

Before beginning, download the latest release of etcd v3.5.

#### Mixed versions

While downgrading, an etcd cluster supports mixed versions of etcd members, and operates with the protocol of the lowest common version. The cluster is considered downgraded once downgrade is enabled by
etcdctl downgrade enable 3.5
. Internally, the overall cluster version is set to the downgrade target version, which controls the reported version and the supported features.

etcdctl downgrade enable 3.5

#### Rollback

Before downgrading your etcd cluster, please create and
download a snapshot backup
of your etcd cluster. This snapshot can be used to restore the cluster to its pre-upgrade state if needed. If users encounter issues during the downgrade, they should first identify and resolve the root cause.

If the downgrade has started after running
etcdctl downgrade enabled
, and the cluster is still in a mixed-version state—where at least one member remains on v3.6, users can cancel the ongoing downgrade process by running
etcdctl downgrade cancel
, and restarting all the downgraded members with the original v3.6 binaries.

etcdctl downgrade enabled

etcdctl downgrade cancel

Once all members have been downgraded to v3.5, the cluster is considered fully downgraded. If users wish to return to the original version after a full downgrade has completed, they should follow the official
upgrade guide
to ensure consistency and avoid data corruption.

### Downgrade procedure

This example shows how to downgrade a 3-member v3.6 etcd cluster running on a local machine.

#### Step 1: check downgrade requirements

Is the cluster healthy and running v3.6.x?

```
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint health
<<COMMENT
localhost:2379 is healthy: successfully committed proposal: took = 2.118638ms
localhost:22379 is healthy: successfully committed proposal: took = 3.631388ms
localhost:32379 is healthy: successfully committed proposal: took = 2.157051ms
COMMENT
curl http://localhost:2379/version
<<COMMENT
{"etcdserver":"3.6.0-alpha.0","etcdcluster":"3.6.0","storage":"3.6.0"}
COMMENT
curl http://localhost:22379/version
<<COMMENT
{"etcdserver":"3.6.0-alpha.0","etcdcluster":"3.6.0","storage":"3.6.0"}
COMMENT
curl http://localhost:32379/version
<<COMMENT
{"etcdserver":"3.6.0-alpha.0","etcdcluster":"3.6.0","storage":"3.6.0"}
COMMENT
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint status -w
=
table
<<COMMENT
+-----------------+------------------+---------------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
|    ENDPOINT     |        ID        |    VERSION    | STORAGE VERSION | DB SIZE | IN USE | PERCENTAGE NOT IN USE | QUOTA | IS LEADER | IS LEARNER | RAFT TERM | RAFT INDEX | RAFT APPLIED INDEX | ERRORS | DOWNGRADE TARGET VERSION | DOWNGRADE ENABLED |
+-----------------+------------------+---------------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
|  localhost:2379 | 8211f1d0f64f3269 | 3.6.0-alpha.0 |           3.6.0 |   20 kB |  16 kB |                   20% |   0 B |      true |      false |         2 |         10 |                 10 |        |                          |             false |
| localhost:22379 | 91bc3c398fb3c146 | 3.6.0-alpha.0 |           3.6.0 |   20 kB |  16 kB |                   20% |   0 B |     false |      false |         2 |         10 |                 10 |        |                          |             false |
| localhost:32379 | fd422379fda50e48 | 3.6.0-alpha.0 |           3.6.0 |   20 kB |  16 kB |                   20% |   0 B |     false |      false |         2 |         10 |                 10 |        |                          |             false |
+-----------------+------------------+---------------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
COMMENT
```

#### Step 2: download snapshot backup from leader

Download the snapshot backup
to provide a downgrade path should any problems occur.

#### Step 3: validate downgrade target version

Validate the downgrade target version before enabling the downgrade:

We only support downgrading one minor version at a time. e.g downgrading from v3.6 to v3.4 isn’t allowed.

Please do not move on to next step until the validation is successful.

```
etcdctl downgrade validate 3.5
<<COMMENT
Downgrade validate success, cluster version 3.6
COMMENT
```

#### Step 4: enable downgrade

```
etcdctl downgrade
enable
3.5
<<COMMENT
Downgrade enable success, cluster version 3.6
COMMENT
```

After enabling downgrade, the cluster will start to operate with v3.5 protocol, which is the downgrade target version. In addition, etcd will automatically migrate the schema to the downgrade target version, which usually happens very fast. Confirm the storage version of all servers has been migrated to v3.5 by checking the endpoint status before moving on to the next step.

```
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint status -w
=
table
<<COMMENT
+-----------------+------------------+---------------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
|    ENDPOINT     |        ID        |    VERSION    | STORAGE VERSION | DB SIZE | IN USE | PERCENTAGE NOT IN USE | QUOTA | IS LEADER | IS LEARNER | RAFT TERM | RAFT INDEX | RAFT APPLIED INDEX | ERRORS | DOWNGRADE TARGET VERSION | DOWNGRADE ENABLED |
+-----------------+------------------+---------------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
|  localhost:2379 | 8211f1d0f64f3269 | 3.6.0-alpha.0 |           3.5.0 |   20 kB |  16 kB |                   20% |   0 B |      true |      false |         2 |         12 |                 12 |        |                    3.5.0 |              true |
| localhost:22379 | 91bc3c398fb3c146 | 3.6.0-alpha.0 |           3.5.0 |   20 kB |  16 kB |                   20% |   0 B |     false |      false |         2 |         12 |                 12 |        |                    3.5.0 |              true |
| localhost:32379 | fd422379fda50e48 | 3.6.0-alpha.0 |           3.5.0 |   20 kB |  16 kB |                   20% |   0 B |     false |      false |         2 |         12 |                 12 |        |                    3.5.0 |              true |
+-----------------+------------------+---------------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
COMMENT
```

Once downgrade is enabled, the cluster will remain operating with v3.5 protocol even if all the servers are still running the v3.6 binary, unless the downgrade is canceled with
etcdctl downgrade cancel

etcdctl downgrade cancel


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Downgrade etcd from v3.6 to v3.5](https://etcd.io/docs/v3.7/downgrades/downgrade_3_6/)
