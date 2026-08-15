---
title: etcd v3.7 抓取：Downgrade etcd from 3.5 to 3.4
date: 2026-09-13 10:20:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/downgrades/downgrade_3_5/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/downgrades/downgrade_3_5/>

---

In the general case, downgrading from etcd 3.5 to 3.4 can be a zero-downtime, rolling downgrade:

one by one, stop the etcd 3.5 processes and replace them with etcd 3.4 processes

after starting any 3.4 processes, new features in 3.5 are not longer available to the cluster

Before
starting a downgrade
, read through the rest of this guide to prepare.

### Downgrade checklists

content/en/docs/v3.5/op-guide/authentication/rbac.md

If your cluster enables auth, rolling downgrade from 3.5 isn’t supported because 3.5
changes a format of WAL entries related to auth
. You can follow the
authentification instructions
to disable auth, and delete all users first.

Highlighted breaking changes from 3.5 to 3.4:

#### Difference in flags

If you are using any of the following flags in your 3.5 configurations, make sure to remove, rename, or change the default value when downgrading to 3.4.

The diff is based on version 3.5.14 and v.3.4.33. The actual diff would be dependent on your patch version, check with
diff <(etcd-3.5/bin/etcd -h | grep \\-\\-) <(etcd-3.4/bin/etcd -h | grep \\-\\-)
first.

diff <(etcd-3.5/bin/etcd -h | grep \\-\\-) <(etcd-3.4/bin/etcd -h | grep \\-\\-)

```
# flags not available in 3.4
-etcd --socket-reuse-port
-etcd --socket-reuse-address
-etcd --raft-read-timeout
-etcd --raft-write-timeout
-etcd --v2-deprecation
-etcd --client-cert-file
-etcd --client-key-file
-etcd --peer-client-cert-file
-etcd --peer-client-key-file
-etcd --self-signed-cert-validity
-etcd --enable-log-rotation --log-rotation-config-json=some.json
-etcd --experimental-enable-distributed-tracing --experimental-distributed-tracing-address='localhost:4317' --experimental-distributed-tracing-service-name='etcd' --experimental-distributed-tracing-instance-id='' --experimental-distributed-tracing-sampling-rate='0'
-etcd --experimental-compact-hash-check-enabled --experimental-compact-hash-check-time='1m'
-etcd --experimental-downgrade-check-time
-etcd --experimental-memory-mlock
-etcd --experimental-txn-mode-write-with-shared-buffer
-etcd --experimental-bootstrap-defrag-threshold-megabytes
-etcd --experimental-stop-grpc-service-on-defrag
# same flag with different names
-etcd --backend-bbolt-freelist-type=map
+etcd --experimental-backend-bbolt-freelist-type=array
# same flag different defaults
-etcd --pre-vote=true
+etcd --pre-vote=false
-etcd --logger=zap
+etcd --logger=capnslog
```

#### etcd --logger zap

etcd --logger zap

3.4 defaults to
--logger=capnslog
while 3.5 defaults
--logger=zap
.

--logger=capnslog

--logger=zap

If you want to keep using
zap
, it needs to be explicitly specified.

zap

```
+etcd --logger=zap --log-outputs=stderr
+# to write logs to stderr and a.log file at the same time
+etcd --logger=zap --log-outputs=stderr,a.log
```

#### Difference in Prometheus metrics

```
# metrics not available in 3.4
-etcd_debugging_mvcc_db_compaction_last
```

### Server downgrade checklists

#### Downgrade requirements

To ensure a smooth rolling downgrade, the running cluster must be healthy. Check the health of the cluster by using the
etcdctl endpoint health
command before proceeding.

etcdctl endpoint health

The 3.4 version to downgrade to must be >= 3.4.32.

#### Preparation

Before downgrading etcd, always test the services relying on etcd in a staging environment before deploying the downgrade to the production environment.

Before beginning,
download the snapshot backup
. Should something go wrong with the downgrade, it is possible to use this backup to
rollback
back to existing etcd version. Please note that the
snapshot
command only backs up the v3 data. For v2 data, see
backing up v2 datastore
.

snapshot

Before beginning, download the latest release of etcd 3.4, and make sure its version is >= 3.4.32.

#### Mixed versions

While downgrading, an etcd cluster supports mixed versions of etcd members, and operates with the protocol of the lowest common version. The cluster is considered downgraded once any of its members is downgraded to version 3.4. Internally, etcd members negotiate with each other to determine the overall cluster version, which controls the reported version and the supported features.

#### Limitations

Note: If the cluster only has v3 data and no v2 data, it is not subject to this limitation.

If the cluster is serving a v2 data set larger than 50MB, each newly downgraded member may take up to two minutes to catch up with the existing cluster. Check the size of a recent snapshot to estimate the total data size. In other words, it is safest to wait for 2 minutes between downgrading each member.

For a much larger total data size, 100MB or more , this one-time process might take even more time. Administrators of very large etcd clusters of this magnitude can feel free to contact the
etcd team
before downgrading, and we’ll be happy to provide advice on the procedure.

#### Rollback

If any member has been downgraded to 3.4, the cluster version will be downgraded to 3.4, and operations will be “3.4” compatible. You would need to follow the
Upgrade etcd from 3.4 to 3.5
instructions to rollback.

Please
download the snapshot backup
to make downgrading the cluster possible even after it has been completely downgraded.

### Downgrade procedure

This example shows how to downgrade a 3-member 3.5 etcd cluster running on a local machine.

#### Step 1: check downgrade requirements

Is the cluster healthy and running 3.5.x?

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
{"etcdserver":"3.5.0","etcdcluster":"3.5.0"}
COMMENT
curl http://localhost:22379/version
<<COMMENT
{"etcdserver":"3.5.0","etcdcluster":"3.5.0"}
COMMENT
curl http://localhost:32379/version
<<COMMENT
{"etcdserver":"3.5.0","etcdcluster":"3.5.0"}
COMMENT
```

#### Step 2: download snapshot backup from leader

Download the snapshot backup
to provide a downgrade path should any problems occur.

#### Step 3: stop one existing etcd server

Before stopping the server, check if it is the leader

```
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint status -w
=
table
<<COMMENT
+-----------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
|    ENDPOINT     |        ID        | VERSION | DB SIZE | IS LEADER | IS LEARNER | RAFT TERM | RAFT INDEX | RAFT APPLIED INDEX | ERRORS |
+-----------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
|  localhost:2379 | 8211f1d0f64f3269 |  3.5.13 |   20 kB |      true |      false |         2 |          9 |                  9 |        |
| localhost:22379 | 91bc3c398fb3c146 |  3.5.13 |   20 kB |     false |      false |         2 |          9 |                  9 |        |
| localhost:32379 | fd422379fda50e48 |  3.5.13 |   20 kB |     false |      false |         2 |          9 |                  9 |        |
+-----------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
COMMENT
```

If the server to be stopped is the leader, you can avoid some downtime by
move-leader
to another server before stopping this server.

move-leader

```
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 move-leader 91bc3c398fb3c146
etcdctl --endpoints
=
localhost:2379,localhost:22379,localhost:32379 endpoint status -w
=
table
<<COMMENT
+-----------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
|    ENDPOINT     |        ID        | VERSION | DB SIZE | IS LEADER | IS LEARNER | RAFT TERM | RAFT INDEX | RAFT APPLIED INDEX | ERRORS |
+-----------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
|  localhost:2379 | 8211f1d0f64f3269 |  3.5.13 |   20 kB |     false |      false |         3 |         11 |                 11 |        |
| localhost:22379 | 91bc3c398fb3c146 |  3.5.13 |   20 kB |      true |      false |         3 |         11 |                 11 |        |
| localhost:32379 | fd422379fda50e48 |  3.5.13 |   20 kB |     false |      false |         3 |         11 |                 11 |        |
+-----------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
COMMENT
```

When each etcd process is stopped, expected errors will be logged by other cluster members. This is normal since a cluster member connection has been (temporarily) broken:

```
{
"level"
:
"info"
,
"ts"
:
"2024-05-14T20:25:47.051124Z"
,
"logger"
:
"raft"
,
"caller"
:
"etcdserver/zap_raft.go:77"
,
"msg"
:
"91bc3c398fb3c146 became leader at term 3"
}
{
"level"
:
"info"
,
"ts"
:
"2024-05-14T20:25:47.051139Z"
,
"logger"
:
"raft"
,
"caller"
:
"etcdserver/zap_raft.go:77"
,
"msg"
:
"raft.node: 91bc3c398fb3c146 elected leader 91bc3c398fb3c146 at term 3"
}
^C
{
"level"
:
"warn"
,
"ts"
:
"2024-05-14T20:27:09.094119Z"
,
"caller"
:
"rafthttp/stream.go:421"
,
"msg"
:
"lost TCP streaming connection with remote peer"
,
"stream-reader-type"
:
"stream MsgApp v2"
,
"local-member-id"
:
"91bc3c398fb3c146"
,
"remote-peer-id"
:
"8211f1d0f64f3269"
,
"error"
:
"EOF"
}
{
"level"
:
"warn"
,
"ts"
:
"2024-05-14T20:27:09.09427Z"
,
"caller"
:
"rafthttp/stream.go:421"
,
"msg"
:
"lost TCP streaming connection with remote peer"
,
"stream-reader-type"
:
"stream Message"
,
"local-member-id"
:
"91bc3c398fb3c146"
,
"remote-peer-id"
:
"8211f1d0f64f3269"
,
"error"
:
"EOF"
}
{
"level"
:
"warn"
,
"ts"
:
"2024-05-14T20:27:09.095535Z"
,
"caller"
:
"rafthttp/peer_status.go:66"
,
"msg"
:
"peer became inactive (message send to peer failed)"
,
"peer-id"
:
"8211f1d0f64f3269"
,
"error"
:
"failed to dial 8211f1d0f64f3269 on stream MsgApp v2 (peer 8211f1d0f64f3269 failed to find local node 91bc3c398fb3c146)"
}
{
"level"
:
"warn"
,
"ts"
:
"2024-05-14T20:27:09.43915Z"
,
"caller"
:
"rafthttp/stream.go:223"
,
"msg"
:
"lost TCP streaming connection with remote peer"
,
"stream-writer-type"
:
"stream Message"
,
"local-member-id"
:
"91bc3c398fb3c146"
,
"remote-peer-id"
:
"8211f1d0f64f3269"
}
{
"level"
:
"warn"
,
"ts"
:
"2024-05-14T20:27:11.085646Z"
,
"caller"
:
"etcdserver/cluster_util.go:294"
,
"msg"
:
"failed to reach the peer URL"
,
"address"
:
"http://127.0.0.1:12380/version"
,
"remote-member-id"
:
"8211f1d0f64f3269"
,
"error"
:
"Get \"http://127.0.0.1:12380/version\": dial tcp 127.0.0.1:12380: connect: connection refused"
}
{
"level"
:
"warn"
,
"ts"
:
"2024-05-14T20:27:11.085718Z"
,
"caller"
:
"etcdserver/cluster_util.go:158"
,
"msg"
:
"failed to get version"
,
"remote-member-id"
:
"8211f1d0f64f3269"
,
"error"
:
"Get \"http://127.0.0.1:12380/version\": dial tcp 127.0.0.1:12380: connect: connection refused"
}
{
"level"
:
"warn"
,
"ts"
:
"2024-05-14T20:27:13.557385Z"
,
"caller"
:
"rafthttp/probing_status.go:68"
,
"msg"
:
"prober detected unhealthy status"
,
"round-tripper-name"
:
"ROUND_TRIPPER_SNAPSHOT"
,
"remote-peer-id"
:
"8211f1d0f64f3269"
,
"rtt"
:
"416.079µs"
,
"error"
:
"dial tcp 127.0.0.1:12380: connect: connection refused"
}
```

#### Step 4: restart the etcd server with same configuration +
--next-cluster-version-compatible

--next-cluster-version-compatible

Restart the etcd server with same configuration but with the new etcd binary and
--next-cluster-version-compatible
.

--next-cluster-version-compatible


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Downgrade etcd from 3.5 to 3.4](https://etcd.io/docs/v3.7/downgrades/downgrade_3_5/)
