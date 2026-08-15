---
title: etcd v3.7 抓取：Upgrade etcd from 3.1 to 3.2
date: 2026-09-13 10:12:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/upgrades/upgrade_3_2/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/upgrades/upgrade_3_2/>

---

In the general case, upgrading from etcd 3.1 to 3.2 can be a zero-downtime, rolling upgrade:

one by one, stop the etcd v3.1 processes and replace them with etcd v3.2 processes

after running all v3.2 processes, new features in v3.2 are available to the cluster

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

Highlighted breaking changes in 3.2.

#### Changed default
snapshot-count
value

snapshot-count

Higher
--snapshot-count
holds more Raft entries in memory until snapshot, thus causing
recurrent higher memory usage
. Since leader retains latest Raft entries for longer, a slow follower has more time to catch up before leader snapshot.
--snapshot-count
is a tradeoff between higher memory usage and better availabilities of slow followers.

--snapshot-count

Since v3.2, the default value of
--snapshot-count
has
changed from from 10,000 to 100,000
.

--snapshot-count

#### Changed gRPC dependency (>=3.2.10)

3.2.10 or later now requires
grpc/grpc-go
v1.7.5
(<=3.2.9 requires
v1.2.1
).

v1.7.5

v1.2.1

grpclog.Logger

grpclog.Logger
has been deprecated in favor of
grpclog.LoggerV2
.
clientv3.Logger
is now
grpclog.LoggerV2
.

grpclog.Logger

grpclog.LoggerV2

clientv3.Logger

grpclog.LoggerV2

Before

```
import
"github.com/coreos/etcd/clientv3"
clientv3
.
SetLogger
(
log
.
New
(
os
.
Stderr
,
"grpc: "
,
0
))
```

After

```
import
"github.com/coreos/etcd/clientv3"
import
"google.golang.org/grpc/grpclog"
clientv3
.
SetLogger
(
grpclog
.
NewLoggerV2
(
os
.
Stderr
,
os
.
Stderr
,
os
.
Stderr
))
// log.New above cannot be used (not implement grpclog.LoggerV2 interface)
```

grpc.ErrClientConnTimeout

Previously,
grpc.ErrClientConnTimeout
error is returned on client dial time-outs. 3.2 instead returns
context.DeadlineExceeded
(see
#8504
).

grpc.ErrClientConnTimeout

context.DeadlineExceeded

Before

```
// expect dial time-out on ipv4 blackhole
_
,
err
:=
clientv3
.
New
(
clientv3
.
Config
{
Endpoints
:
[]
string
{
"http://254.0.0.1:12345"
},
DialTimeout
:
2
*
time
.
Second
})
if
err
==
grpc
.
ErrClientConnTimeout
{
// handle errors
}
```

After

```
_
,
err
:=
clientv3
.
New
(
clientv3
.
Config
{
Endpoints
:
[]
string
{
"http://254.0.0.1:12345"
},
DialTimeout
:
2
*
time
.
Second
})
if
err
==
context
.
DeadlineExceeded
{
// handle errors
}
```

#### Changed maximum request size limits (>=3.2.10)

3.2.10 and 3.2.11 allow custom request size limits in server side. >=3.2.12 allows custom request size limits for both server and
client side
. In previous versions(v3.2.10, v3.2.11), client response size was limited to only 4 MiB.

Server-side request limits can be configured with
--max-request-bytes
flag:

--max-request-bytes

```
# limits request size to 1.5 KiB
etcd --max-request-bytes
1536
# client writes exceeding 1.5 KiB will be rejected
etcdctl put foo
[
LARGE VALUE...
]
# etcdserver: request is too large
```

Or configure
embed.Config.MaxRequestBytes
field:

embed.Config.MaxRequestBytes

```
import
"github.com/coreos/etcd/embed"
import
"github.com/coreos/etcd/etcdserver/api/v3rpc/rpctypes"
// limit requests to 5 MiB
cfg
:=
embed
.
NewConfig
()
cfg
.
MaxRequestBytes
=
5
*
1024
*
1024
// client writes exceeding 5 MiB will be rejected
_
,
err
:=
cli
.
Put
(
ctx
,
"foo"
,
[
LARGE
VALUE
...
])
err
==
rpctypes
.
ErrRequestTooLarge
```

If not specified, server-side limit defaults to 1.5 MiB
.

Client-side request limits must be configured based on server-side limits.

```
# limits request size to 1 MiB
etcd --max-request-bytes
1048576
```

```
import
"github.com/coreos/etcd/clientv3"
cli
,
_
:=
clientv3
.
New
(
clientv3
.
Config
{
Endpoints
:
[]
string
{
"127.0.0.1:2379"
},
MaxCallSendMsgSize
:
2
*
1024
*
1024
,
MaxCallRecvMsgSize
:
3
*
1024
*
1024
,
})
// client writes exceeding "--max-request-bytes" will be rejected from etcd server
_
,
err
:=
cli
.
Put
(
ctx
,
"foo"
,
strings
.
Repeat
(
"a"
,
1
*
1024
*
1024
+
5
))
err
==
rpctypes
.
ErrRequestTooLarge
// client writes exceeding "MaxCallSendMsgSize" will be rejected from client-side
_
,
err
=
cli
.
Put
(
ctx
,
"foo"
,
strings
.
Repeat
(
"a"
,
5
*
1024
*
1024
))
err
.
Error
()
==
"rpc error: code = ResourceExhausted desc = grpc: trying to send message larger than max (5242890 vs. 2097152)"
// some writes under limits
for
i
:=
range
[]
int
{
0
,
1
,
2
,
3
,
4
}
{
_
,
err
=
cli
.
Put
(
ctx
,
fmt
.
Sprintf
(
"foo%d"
,
i
),
strings
.
Repeat
(
"a"
,
1
*
1024
*
1024
-
500
))
if
err
!=
nil
{
panic
(
err
)
}
}
// client reads exceeding "MaxCallRecvMsgSize" will be rejected from client-side
_
,
err
=
cli
.
Get
(
ctx
,
"foo"
,
clientv3
.
WithPrefix
())
err
.
Error
()
==
"rpc error: code = ResourceExhausted desc = grpc: received message larger than max (5240509 vs. 3145728)"
```

If not specified, client-side send limit defaults to 2 MiB (1.5 MiB + gRPC overhead bytes) and receive limit to
math.MaxInt32
. Please see
clientv3 godoc
for more detail.

math.MaxInt32

#### Changed raw gRPC client wrappers

3.2.12 or later changes the function signatures of
clientv3
gRPC client wrapper. This change was needed to support
custom
grpc.CallOption
on message size limits
.

clientv3

grpc.CallOption

Before and after

```
-func NewKVFromKVClient(remote pb.KVClient) KV {
+func NewKVFromKVClient(remote pb.KVClient, c *Client) KV {
-func NewClusterFromClusterClient(remote pb.ClusterClient) Cluster {
+func NewClusterFromClusterClient(remote pb.ClusterClient, c *Client) Cluster {
-func NewLeaseFromLeaseClient(remote pb.LeaseClient, keepAliveTimeout time.Duration) Lease {
+func NewLeaseFromLeaseClient(remote pb.LeaseClient, c *Client, keepAliveTimeout time.Duration) Lease {
-func NewMaintenanceFromMaintenanceClient(remote pb.MaintenanceClient) Maintenance {
+func NewMaintenanceFromMaintenanceClient(remote pb.MaintenanceClient, c *Client) Maintenance {
-func NewWatchFromWatchClient(wc pb.WatchClient) Watcher {
+func NewWatchFromWatchClient(wc pb.WatchClient, c *Client) Watcher {
```

#### Changed
clientv3.Lease.TimeToLive
API

clientv3.Lease.TimeToLive

Previously,
clientv3.Lease.TimeToLive
API returned
lease.ErrLeaseNotFound
on non-existent lease ID. 3.2 instead returns TTL=-1 in its response and no error (see
#7305
).

clientv3.Lease.TimeToLive

lease.ErrLeaseNotFound

Before

```
// when leaseID does not exist
resp
,
err
:=
TimeToLive
(
ctx
,
leaseID
)
resp
==
nil
err
==
lease
.
ErrLeaseNotFound
```

After

```
// when leaseID does not exist
resp
,
err
:=
TimeToLive
(
ctx
,
leaseID
)
resp
.
TTL
==
-
1
err
==
nil
```

#### Moved
clientv3.NewFromConfigFile
to
clientv3.yaml.NewConfig

clientv3.NewFromConfigFile

clientv3.yaml.NewConfig

clientv3.NewFromConfigFile
is moved to
yaml.NewConfig
.

clientv3.NewFromConfigFile

yaml.NewConfig

Before

```
import
"github.com/coreos/etcd/clientv3"
clientv3
.
NewFromConfigFile
```

After

```
import
clientv3yaml
"github.com/coreos/etcd/clientv3/yaml"
clientv3yaml
.
NewConfig
```

#### Change in
--listen-peer-urls
and
--listen-client-urls

--listen-peer-urls

--listen-client-urls

3.2 now rejects domains names for
--listen-peer-urls
and
--listen-client-urls
(3.1 only prints out warnings), since domain name is invalid for network interface binding. Make sure that those URLs are properly formatted as
scheme://IP:port
.

--listen-peer-urls

--listen-client-urls

scheme://IP:port

See
issue #6336
for more contexts.

### Server upgrade checklists

#### Upgrade requirements

To upgrade an existing etcd deployment to 3.2, the running cluster must be 3.1 or greater. If it’s before 3.1, please
upgrade to 3.1
before upgrading to 3.2.

Also, to ensure a smooth rolling upgrade, the running cluster must be healthy. Check the health of the cluster by using the
etcdctl endpoint health
command before proceeding.

etcdctl endpoint health

#### Preparation

Before upgrading etcd, always test the services relying on etcd in a staging environment before deploying the upgrade to the production environment.

Before beginning,
backup the etcd data
. Should something go wrong with the upgrade, it is possible to use this backup to
downgrade
back to existing etcd version. Please note that the
snapshot
command only backs up the v3 data. For v2 data, see
backing up v2 datastore
.

snapshot

#### Mixed versions

While upgrading, an etcd cluster supports mixed versions of etcd members, and operates with the protocol of the lowest common version. The cluster is only considered upgraded once all of its members are upgraded to version 3.2. Internally, etcd members negotiate with each other to determine the overall cluster version, which controls the reported version and the supported features.

#### Limitations

Note: If the cluster only has v3 data and no v2 data, it is not subject to this limitation.

If the cluster is serving a v2 data set larger than 50MB, each newly upgraded member may take up to two minutes to catch up with the existing cluster. Check the size of a recent snapshot to estimate the total data size. In other words, it is safest to wait for 2 minutes between upgrading each member.

For a much larger total data size, 100MB or more , this one-time process might take even more time. Administrators of very large etcd clusters of this magnitude can feel free to contact the
etcd team
before upgrading, and we’ll be happy to provide advice on the procedure.

#### Downgrade

If all members have been upgraded to v3.2, the cluster will be upgraded to v3.2, and downgrade from this completed state is
not possible
. If any single member is still v3.1, however, the cluster and its operations remains “v3.1”, and it is possible from this mixed cluster state to return to using a v3.1 etcd binary on all members.

Please
backup the data directory
of all etcd members to make downgrading the cluster possible even after it has been completely upgraded.

### Upgrade procedure

This example shows how to upgrade a 3-member v3.1 etcd cluster running on a local machine.

#### 1. Check upgrade requirements

Is the cluster healthy and running v3.1.x?

```
$ ETCDCTL_API=3 etcdctl endpoint health --endpoints=localhost:2379,localhost:22379,localhost:32379
localhost:2379 is healthy: successfully committed proposal: took = 6.600684ms
localhost:22379 is healthy: successfully committed proposal: took = 8.540064ms
localhost:32379 is healthy: successfully committed proposal: took = 8.763432ms

$ curl http://localhost:2379/version
{"etcdserver":"3.1.7","etcdcluster":"3.1.0"}
```

#### 2. Stop the existing etcd process

When each etcd process is stopped, expected errors will be logged by other cluster members. This is normal since a cluster member connection has been (temporarily) broken:


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Upgrade etcd from 3.1 to 3.2](https://etcd.io/docs/v3.7/upgrades/upgrade_3_2/)
