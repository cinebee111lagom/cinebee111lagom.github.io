---
title: etcd v3.7 抓取：Upgrade etcd from 3.4 to 3.5
date: 2026-09-13 10:15:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/upgrades/upgrade_3_5/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/upgrades/upgrade_3_5/>

---

In the general case, upgrading from etcd 3.4 to 3.5 can be a zero-downtime, rolling upgrade:

one by one, stop the etcd v3.4 processes and replace them with etcd v3.5 processes

after running all v3.5 processes, new features in v3.5 are available to the cluster

Before
starting an upgrade
, read through the rest of this guide to prepare.

### Upgrade checklists

When
migrating from v2 with no v3 data
, etcd server v3.2+ panics when etcd restores from existing snapshots but no v3
ETCD_DATA_DIR/member/snap/db
file. This happens when the server had migrated from v2 with no previous v3 data. This also prevents accidental v3 data loss (e.g.
db
file might have been moved). etcd requires that post v3 migration can only happen with v3 data. Do not upgrade to newer v3 versions until v3.0 server contains v3 data.

ETCD_DATA_DIR/member/snap/db

db

If your cluster enables auth, rolling upgrade from 3.4 or older version isn’t supported because 3.5
changes a format of WAL entries related to auth
.

Highlighted breaking changes in 3.5.

#### Deprecated
etcd_debugging_mvcc_db_total_size_in_bytes
Prometheus metrics

etcd_debugging_mvcc_db_total_size_in_bytes

v3.5 promoted
etcd_debugging_mvcc_db_total_size_in_bytes
Prometheus metrics to
etcd_mvcc_db_total_size_in_bytes
, in order to encourage etcd storage monitoring. And v3.5 completely deprecates
etcd_debugging_mvcc_db_total_size_in_bytes
.

etcd_debugging_mvcc_db_total_size_in_bytes

etcd_mvcc_db_total_size_in_bytes

etcd_debugging_mvcc_db_total_size_in_bytes

```
-etcd_debugging_mvcc_db_total_size_in_bytes
+etcd_mvcc_db_total_size_in_bytes
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecated
etcd_debugging_mvcc_put_total
Prometheus metrics

etcd_debugging_mvcc_put_total

v3.5 promoted
etcd_debugging_mvcc_put_total
Prometheus metrics to
etcd_mvcc_put_total
, in order to encourage etcd storage monitoring. And v3.5 completely deprecates
etcd_debugging_mvcc_put_total
.

etcd_debugging_mvcc_put_total

etcd_mvcc_put_total

etcd_debugging_mvcc_put_total

```
-etcd_debugging_mvcc_put_total
+etcd_mvcc_put_total
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecated
etcd_debugging_mvcc_delete_total
Prometheus metrics

etcd_debugging_mvcc_delete_total

v3.5 promoted
etcd_debugging_mvcc_delete_total
Prometheus metrics to
etcd_mvcc_delete_total
, in order to encourage etcd storage monitoring. And v3.5 completely deprecates
etcd_debugging_mvcc_delete_total
.

etcd_debugging_mvcc_delete_total

etcd_mvcc_delete_total

etcd_debugging_mvcc_delete_total

```
-etcd_debugging_mvcc_delete_total
+etcd_mvcc_delete_total
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecated
etcd_debugging_mvcc_txn_total
Prometheus metrics

etcd_debugging_mvcc_txn_total

v3.5 promoted
etcd_debugging_mvcc_txn_total
Prometheus metrics to
etcd_mvcc_txn_total
, in order to encourage etcd storage monitoring. And v3.5 completely deprecates
etcd_debugging_mvcc_txn_total
.

etcd_debugging_mvcc_txn_total

etcd_mvcc_txn_total

etcd_debugging_mvcc_txn_total

```
-etcd_debugging_mvcc_txn_total
+etcd_mvcc_txn_total
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecated
etcd_debugging_mvcc_range_total
Prometheus metrics

etcd_debugging_mvcc_range_total

v3.5 promoted
etcd_debugging_mvcc_range_total
Prometheus metrics to
etcd_mvcc_range_total
, in order to encourage etcd storage monitoring. And v3.5 completely deprecates
etcd_debugging_mvcc_range_total
.

etcd_debugging_mvcc_range_total

etcd_mvcc_range_total

etcd_debugging_mvcc_range_total

```
-etcd_debugging_mvcc_range_total
+etcd_mvcc_range_total
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecated
etcd --logger capnslog

etcd --logger capnslog

v3.4 defaults to
--logger=zap
in order to support multiple log outputs and structured logging.

--logger=zap

etcd --logger=capnslog
has been deprecated in v3.5
, and now
--logger=zap
is the default.

etcd --logger=capnslog

--logger=zap

```
-etcd --logger=capnslog
+etcd --logger=zap --log-outputs=stderr
+# to write logs to stderr and a.log file at the same time
+etcd --logger=zap --log-outputs=stderr,a.log
```

v3.4 adds
etcd --logger=zap
support for structured logging and multiple log outputs. Main motivation is to promote automated etcd monitoring, rather than looking back server logs when it starts breaking. Future development will make etcd log as few as possible, and make etcd easier to monitor with metrics and alerts.
etcd --logger=capnslog
will be deprecated in v3.5.

etcd --logger=zap

etcd --logger=capnslog

#### Deprecated
etcd --log-output

etcd --log-output

v3.4 renamed
etcd --log-output
to
--log-outputs
to support multiple log outputs.

etcd --log-output

--log-outputs

etcd --log-output
has been deprecated in v3.5.

etcd --log-output

```
-etcd --log-output=stderr
+etcd --log-outputs=stderr
```

#### Deprecated
etcd --debug
flag (now
--log-level=debug
)

etcd --debug

--log-level=debug

etcd --debug
flag has been deprecated.

etcd --debug

```
-etcd --debug
+etcd --log-level debug
```

#### Deprecated
etcd --log-package-levels

etcd --log-package-levels

etcd --log-package-levels
flag for
capnslog
has been deprecated.

etcd --log-package-levels

capnslog

Now,
etcd --logger=zap
is the default.

etcd --logger=zap

```
-etcd --log-package-levels 'etcdmain=CRITICAL,etcdserver=DEBUG'
+etcd --logger=zap --log-outputs=stderr
```

#### Deprecated
[CLIENT-URL]/config/local/log

[CLIENT-URL]/config/local/log

/config/local/log
endpoint is being deprecated in v3.5, as is
etcd --log-package-levels
flag.

/config/local/log

etcd --log-package-levels

```
-$ curl http://127.0.0.1:2379/config/local/log -XPUT -d '{"Level":"DEBUG"}'
-# debug logging enabled
```

#### Changed gRPC gateway HTTP endpoints (deprecated
/v3beta
)

/v3beta

Before

```
curl -L http://localhost:2379/v3beta/kv/put
\
-X POST -d
'{"key": "Zm9v", "value": "YmFy"}'
```

After

```
curl -L http://localhost:2379/v3/kv/put
\
-X POST -d
'{"key": "Zm9v", "value": "YmFy"}'
```

/v3beta
has been removed in 3.5 release.

/v3beta

### Server upgrade checklists

#### Upgrade requirements

To upgrade an existing etcd deployment to 3.5, the running cluster must be 3.4 or greater. If it’s before 3.4, please
upgrade to 3.4
before upgrading to 3.5.

Also, to ensure a smooth rolling upgrade, the running cluster must be healthy. Check the health of the cluster by using the
etcdctl endpoint health
command before proceeding.

etcdctl endpoint health

#### Preparation

Before upgrading etcd, always test the services relying on etcd in a staging environment before deploying the upgrade to the production environment.

Before beginning,
download the snapshot backup
. Should something go wrong with the upgrade, it is possible to use this backup to
downgrade
back to existing etcd version. Please note that the
snapshot
command only backs up the v3 data. For v2 data, see
backing up v2 datastore
.

snapshot

#### Mixed versions

While upgrading, an etcd cluster supports mixed versions of etcd members, and operates with the protocol of the lowest common version. The cluster is only considered upgraded once all of its members are upgraded to version 3.5. Internally, etcd members negotiate with each other to determine the overall cluster version, which controls the reported version and the supported features.

#### Limitations

Note: If the cluster only has v3 data and no v2 data, it is not subject to this limitation.

If the cluster is serving a v2 data set larger than 50MB, each newly upgraded member may take up to two minutes to catch up with the existing cluster. Check the size of a recent snapshot to estimate the total data size. In other words, it is safest to wait for 2 minutes between upgrading each member.

For a much larger total data size, 100MB or more , this one-time process might take even more time. Administrators of very large etcd clusters of this magnitude can feel free to contact the
etcd team
before upgrading, and we’ll be happy to provide advice on the procedure.

#### Downgrade

If all members have been upgraded to v3.5, the cluster will be upgraded to v3.5, and downgrade from this completed state is
not possible
. If any single member is still v3.4, however, the cluster and its operations remains “v3.4”, and it is possible from this mixed cluster state to return to using a v3.4 etcd binary on all members.

Please
download the snapshot backup
to make downgrading the cluster possible even after it has been completely upgraded.

### Upgrade procedure

This example shows how to upgrade a 3-member v3.4 etcd cluster running on a local machine.

#### Step 1: check upgrade requirements

Is the cluster healthy and running v3.4.x?

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
{"etcdserver":"3.4.0","etcdcluster":"3.4.0"}
COMMENT
curl http://localhost:22379/version
<<COMMENT
{"etcdserver":"3.4.0","etcdcluster":"3.4.0"}
COMMENT
curl http://localhost:32379/version
<<COMMENT
{"etcdserver":"3.4.0","etcdcluster":"3.4.0"}
COMMENT
```

#### Step 2: download snapshot backup from leader

Download the snapshot backup
to provide a downgrade path should any problems occur.

etcd leader is guaranteed to have the latest application data, thus fetch snapshot from leader:

```
curl -sL http://localhost:2379/metrics
|
grep etcd_server_is_leader
<<COMMENT
# HELP etcd_server_is_leader Whether or not this member is a leader. 1 if is, 0 otherwise.
# TYPE etcd_server_is_leader gauge
etcd_server_is_leader 1
COMMENT
curl -sL http://localhost:22379/metrics
|
grep etcd_server_is_leader
<<COMMENT
etcd_server_is_leader 0
COMMENT
curl -sL http://localhost:32379/metrics
|
grep etcd_server_is_leader
<<COMMENT
etcd_server_is_leader 0
COMMENT
etcdctl --endpoints
=
localhost:2379 snapshot save backup.db
<<COMMENT
{"level":"info","ts":1526585787.148433,"caller":"snapshot/v3_snapshot.go:109","msg":"created temporary db file","path":"backup.db.part"}
{"level":"info","ts":1526585787.1485257,"caller":"snapshot/v3_snapshot.go:120","msg":"fetching snapshot","endpoint":"localhost:2379"}
{"level":"info","ts":1526585787.1519694,"caller":"snapshot/v3_snapshot.go:133","msg":"fetched snapshot","endpoint":"localhost:2379","took":0.003502721}
{"level":"info","ts":1526585787.1520295,"caller":"snapshot/v3_snapshot.go:142","msg":"saved","path":"backup.db"}
Snapshot saved at backup.db
COMMENT
```

#### Step 3: stop one existing etcd server

When each etcd process is stopped, expected errors will be logged by other cluster members. This is normal since a cluster member connection has been (temporarily) broken:


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Upgrade etcd from 3.4 to 3.5](https://etcd.io/docs/v3.7/upgrades/upgrade_3_5/)
