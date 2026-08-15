---
title: etcd v3.7 抓取：Downgrade etcd from v3.7 to v3.6
date: 2026-09-13 10:22:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/downgrades/downgrade_3_7/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/downgrades/downgrade_3_7/>

---

In the general case, downgrading from etcd v3.7 to v3.6 can be a zero-downtime, rolling downgrade:

one by one, stop the etcd v3.7 processes and replace them with etcd v3.6 processes

after enabling the downgrade, new features in v3.7 are no longer available to the cluster

Before
starting a downgrade
, read through the rest of this guide to prepare.

### Downgrade checklists

Highlighted differences between v3.7 and v3.6:

#### Difference in flags

v3.7 does not introduce any new flags, so a v3.6 process accepts every flag of a v3.7 configuration and no configuration changes are required when downgrading.

The diff is based on version v3.7.0-rc.0 and v3.6.13. The actual diff would be dependent on your patch version, check with
diff <(etcd-3.7/bin/etcd -h | grep \\-\\-) <(etcd-3.6/bin/etcd -h | grep \\-\\-)
first.

diff <(etcd-3.7/bin/etcd -h | grep \\-\\-) <(etcd-3.6/bin/etcd -h | grep \\-\\-)

The deprecated
--experimental-*
flags that were removed in v3.7 still exist in v3.6, but do not re-add them after the downgrade; use their non-experimental equivalents or
--feature-gates
entries, which work on both versions.

--experimental-*

--feature-gates

#### Difference in Prometheus metrics

```
# metrics not available in v3.6
-etcd_server_request_duration_seconds
-etcd_debugging_server_watch_send_loop_control_stream_duration_seconds
-etcd_debugging_server_watch_send_loop_progress_duration_seconds
-etcd_debugging_server_watch_send_loop_watch_stream_duration_seconds
-etcd_debugging_server_watch_send_loop_watch_stream_duration_per_event_seconds
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

Before beginning, download the latest release of etcd v3.6.

#### Mixed versions

While downgrading, an etcd cluster supports mixed versions of etcd members, and operates with the protocol of the lowest common version. The cluster is considered downgraded once downgrade is enabled by
etcdctl downgrade enable 3.6
. Internally, the overall cluster version is set to the downgrade target version, which controls the reported version and the supported features.

etcdctl downgrade enable 3.6

#### Rollback

Before downgrading your etcd cluster, please create and
download a snapshot backup
of your etcd cluster. This snapshot can be used to restore the cluster to its pre-downgrade state if needed. If users encounter issues during the downgrade, they should first identify and resolve the root cause.

If the downgrade has started after running
etcdctl downgrade enable
, and the cluster is still in a mixed-version state, where at least one member remains on v3.7, users can cancel the ongoing downgrade process by running
etcdctl downgrade cancel
, and restarting all the downgraded members with the original v3.7 binaries.

etcdctl downgrade enable

etcdctl downgrade cancel

Once all members have been downgraded to v3.6, the cluster is considered fully downgraded. If users wish to return to the original version after a full downgrade has completed, they should follow the official
upgrade guide
to ensure consistency and avoid data corruption.

### Downgrade procedure

This example shows how to downgrade a 3-member v3.7 etcd cluster running on a local machine. The output below is from a real run against etcd v3.7.0-rc.0 and etcd v3.6.13 on a single host with three loopback ports, on a cluster that was upgraded from v3.6.13 shortly before.

#### Step 1: check downgrade requirements

Is the cluster healthy and running v3.7.x?

```
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint health
<<COMMENT
localhost:2379 is healthy: successfully committed proposal: took = 1.052416ms
localhost:32379 is healthy: successfully committed proposal: took = 1.11625ms
localhost:22379 is healthy: successfully committed proposal: took = 1.114291ms
COMMENT
curl http://localhost:2379/version
<<COMMENT
{"etcdserver":"3.7.0-rc.0","etcdcluster":"3.7.0","storage":"3.7.0"}
COMMENT
curl http://localhost:22379/version
<<COMMENT
{"etcdserver":"3.7.0-rc.0","etcdcluster":"3.7.0","storage":"3.7.0"}
COMMENT
curl http://localhost:32379/version
<<COMMENT
{"etcdserver":"3.7.0-rc.0","etcdcluster":"3.7.0","storage":"3.7.0"}
COMMENT
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint status -w
=
table
<<COMMENT
+-----------------+------------------+------------+-----------------+---------+--------+-----------------------+--------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
|    ENDPOINT     |        ID        |  VERSION   | STORAGE VERSION | DB SIZE | IN USE | PERCENTAGE NOT IN USE | QUOTA  | IS LEADER | IS LEARNER | RAFT TERM | RAFT INDEX | RAFT APPLIED INDEX | ERRORS | DOWNGRADE TARGET VERSION | DOWNGRADE ENABLED |
+-----------------+------------------+------------+-----------------+---------+--------+-----------------------+--------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
|  localhost:2379 | 7339c4e5e833c029 | 3.7.0-rc.0 |           3.7.0 |   98 kB |  98 kB |                    0% | 2.1 GB |      true |      false |         5 |         20 |                 20 |        |                          |             false |
| localhost:22379 | 729934363faa4a24 | 3.7.0-rc.0 |           3.7.0 |   98 kB |  98 kB |                    0% | 2.1 GB |     false |      false |         5 |         20 |                 20 |        |                          |             false |
| localhost:32379 |  b548c2511513015 | 3.7.0-rc.0 |           3.7.0 |   98 kB |  98 kB |                    0% | 2.1 GB |     false |      false |         5 |         20 |                 20 |        |                          |             false |
+-----------------+------------------+------------+-----------------+---------+--------+-----------------------+--------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
COMMENT
```

#### Step 2: download snapshot backup from leader

Download the snapshot backup
to provide a downgrade path should any problems occur:

```
etcdctl --endpoints
=
localhost:2379 snapshot save backup.db
<<COMMENT
{"level":"info","ts":"2026-07-02T06:48:11.091982+0300","caller":"snapshot/v3_snapshot.go:83","msg":"created temporary db file","path":"backup.db.part"}
{"level":"info","ts":"2026-07-02T06:48:11.092253+0300","logger":"client","caller":"v3/maintenance.go:236","msg":"opened snapshot stream; downloading"}
{"level":"info","ts":"2026-07-02T06:48:11.099884+0300","caller":"snapshot/v3_snapshot.go:96","msg":"fetching snapshot","endpoint":"localhost:2379"}
{"level":"info","ts":"2026-07-02T06:48:11.100394+0300","logger":"client","caller":"v3/maintenance.go:302","msg":"completed snapshot read; closing"}
{"level":"info","ts":"2026-07-02T06:48:11.103116+0300","caller":"snapshot/v3_snapshot.go:111","msg":"fetched snapshot","endpoint":"localhost:2379","size":"98 kB","took":"10.9815ms","etcd-version":"3.7.0"}
{"level":"info","ts":"2026-07-02T06:48:11.103296+0300","caller":"snapshot/v3_snapshot.go:121","msg":"saved","path":"backup.db"}
Snapshot saved at backup.db
Server version 3.7.0
COMMENT
```

#### Step 3: validate downgrade target version

Validate the downgrade target version before enabling the downgrade:

We only support downgrading one minor version at a time. e.g downgrading from v3.7 to v3.5 isn’t allowed.

Please do not move on to next step until the validation is successful.

```
etcdctl downgrade validate 3.6
<<COMMENT
Downgrade validate success, cluster version 3.7
COMMENT
```

#### Step 4: enable downgrade

```
etcdctl downgrade
enable
3.6
<<COMMENT
Downgrade enable success, cluster version 3.7
COMMENT
```

After enabling downgrade, the cluster will start to operate with v3.6 protocol, which is the downgrade target version. In addition, etcd will automatically migrate the schema to the downgrade target version, which usually happens very fast. Confirm the storage version of all servers has been migrated to v3.6 by checking the endpoint status before moving on to the next step.

```
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint status -w
=
table
<<COMMENT
+-----------------+------------------+------------+-----------------+---------+--------+-----------------------+--------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
|    ENDPOINT     |        ID        |  VERSION   | STORAGE VERSION | DB SIZE | IN USE | PERCENTAGE NOT IN USE | QUOTA  | IS LEADER | IS LEARNER | RAFT TERM | RAFT INDEX | RAFT APPLIED INDEX | ERRORS | DOWNGRADE TARGET VERSION | DOWNGRADE ENABLED |
+-----------------+------------------+------------+-----------------+---------+--------+-----------------------+--------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
|  localhost:2379 | 7339c4e5e833c029 | 3.7.0-rc.0 |           3.6.0 |   98 kB |  98 kB |                    0% | 2.1 GB |      true |      false |         5 |         22 |                 22 |        |                    3.6.0 |              true |
| localhost:22379 | 729934363faa4a24 | 3.7.0-rc.0 |           3.6.0 |   98 kB |  98 kB |                    0% | 2.1 GB |     false |      false |         5 |         22 |                 22 |        |                    3.6.0 |              true |
| localhost:32379 |  b548c2511513015 | 3.7.0-rc.0 |           3.6.0 |   98 kB |  98 kB |                    0% | 2.1 GB |     false |      false |         5 |         22 |                 22 |        |                    3.6.0 |              true |
+-----------------+------------------+------------+-----------------+---------+--------+-----------------------+--------+-----------+------------+-----------+------------+--------------------+--------+--------------------------+-------------------+
COMMENT
```

Once downgrade is enabled, the cluster will remain operating with v3.6 protocol even if all the servers are still running the v3.7 binary, unless the downgrade is canceled with
etcdctl downgrade cancel

etcdctl downgrade cancel

#### Step 5: stop one existing etcd server

Before stopping the server, check if it is the leader. We recommend downgrading the leader last. If the server to be stopped is the leader, you can avoid some downtime by
move-leader
to another server before stopping this server.

move-leader

```
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 move-leader 729934363faa4a24
<<COMMENT
Leadership transferred from 7339c4e5e833c029 to 729934363faa4a24
COMMENT
```

When each etcd process is stopped, expected errors will be logged by other cluster members. This is normal since a cluster member connection has been (temporarily) broken:


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Downgrade etcd from v3.7 to v3.6](https://etcd.io/docs/v3.7/downgrades/downgrade_3_7/)
