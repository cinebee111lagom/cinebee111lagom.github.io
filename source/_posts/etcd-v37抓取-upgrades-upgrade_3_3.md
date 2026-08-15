---
title: etcd v3.7 抓取：Upgrade etcd from 3.2 to 3.3
date: 2026-09-13 10:13:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/upgrades/upgrade_3_3/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/upgrades/upgrade_3_3/>

---

In the general case, upgrading from etcd 3.2 to 3.3 can be a zero-downtime, rolling upgrade:

one by one, stop the etcd v3.2 processes and replace them with etcd v3.3 processes

after running all v3.3 processes, new features in v3.3 are available to the cluster

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

if you enable auth and use lease(lease ttl is small), it has a high probability to encounter
issue
that will result in data inconsistency. It is strongly recommended upgrading to 3.2.31+ firstly to fix this problem, and then upgrade to 3.3. In addition, if the user without permission sends a
LeaseRevoke
request to the 3.3 node during the upgrade process, it may still cause data corruption, so it is best to ensure that your environment doesn’t exist such abnormal calls before upgrading, see
#11691
for detail.

LeaseRevoke

Highlighted breaking changes in 3.3.

#### Changed value type of
etcd --auto-compaction-retention
flag to
string

etcd --auto-compaction-retention

string

Changed
--auto-compaction-retention
flag to
accept string values
with
finer granularity
. Now that
--auto-compaction-retention
accepts string values, etcd configuration YAML file
auto-compaction-retention
field must be changed to
string
type. Previously,
--config-file etcd.config.yaml
can have
auto-compaction-retention: 24
field, now must be
auto-compaction-retention: "24"
or
auto-compaction-retention: "24h"
. If configured as
--auto-compaction-mode periodic --auto-compaction-retention "24h"
, the time duration value for
--auto-compaction-retention
flag must be valid for
time.ParseDuration
function in Go.

--auto-compaction-retention

auto-compaction-retention

string

--config-file etcd.config.yaml

auto-compaction-retention: 24

auto-compaction-retention: "24"

auto-compaction-retention: "24h"

--auto-compaction-mode periodic --auto-compaction-retention "24h"

--auto-compaction-retention

time.ParseDuration

```
# etcd.config.yaml
+auto-compaction-mode: periodic
-auto-compaction-retention: 24
+auto-compaction-retention: "24"
+# Or
+auto-compaction-retention: "24h"
```

#### Changed
etcdserver.EtcdServer.ServerConfig
to
*etcdserver.EtcdServer.ServerConfig

etcdserver.EtcdServer.ServerConfig

*etcdserver.EtcdServer.ServerConfig

etcdserver.EtcdServer
has changed the type of its member field
*etcdserver.ServerConfig
to
etcdserver.ServerConfig
. And
etcdserver.NewServer
now takes
etcdserver.ServerConfig
, instead of
*etcdserver.ServerConfig
.

etcdserver.EtcdServer

*etcdserver.ServerConfig

etcdserver.ServerConfig

etcdserver.NewServer

etcdserver.ServerConfig

*etcdserver.ServerConfig

Before and after (e.g.
k8s.io/kubernetes/test/e2e_node/services/etcd.go
)

```
import "github.com/coreos/etcd/etcdserver"
type EtcdServer struct {
*etcdserver.EtcdServer
-	config *etcdserver.ServerConfig
+	config etcdserver.ServerConfig
}
func NewEtcd(dataDir string) *EtcdServer {
-	config := &etcdserver.ServerConfig{
+	config := etcdserver.ServerConfig{
DataDir: dataDir,
...
}
return &EtcdServer{config: config}
}
func (e *EtcdServer) Start() error {
var err error
e.EtcdServer, err = etcdserver.NewServer(e.config)
...
```

#### Added
embed.Config.LogOutput
struct

embed.Config.LogOutput

Note that this field has been renamed to
embed.Config.LogOutputs
in
[]string
type in v3.4. Please see
v3.4 upgrade guide
for more details.

embed.Config.LogOutputs

[]string

Field
LogOutput
is added to
embed.Config
:

LogOutput

embed.Config

```
package embed
type Config struct {
Debug bool `json:"debug"`
LogPkgLevels string `json:"log-package-levels"`
+	LogOutput string `json:"log-output"`
...
```

Before gRPC server warnings were logged in etcdserver.

```
WARNING: 2017/11/02 11:35:51 grpc: addrConn.resetTransport failed to create client transport: connection error: desc = "transport: Error while dialing dial tcp: operation was canceled"; Reconnecting to {localhost:2379 <nil>}
WARNING: 2017/11/02 11:35:51 grpc: addrConn.resetTransport failed to create client transport: connection error: desc = "transport: Error while dialing dial tcp: operation was canceled"; Reconnecting to {localhost:2379 <nil>}
```

From v3.3, gRPC server logs are disabled by default.

Note that
embed.Config.SetupLogging
method has been deprecated in v3.4. Please see
v3.4 upgrade guide
for more details.

embed.Config.SetupLogging

```
import
"github.com/coreos/etcd/embed"
cfg
:=
&
embed
.
Config
{
Debug
:
false
}
cfg
.
SetupLogging
()
```

Set
embed.Config.Debug
field to
true
to enable gRPC server logs.

embed.Config.Debug

true

#### Changed
/health
endpoint response

/health

Previously,
[endpoint]:[client-port]/health
returned manually marshaled JSON value. 3.3 now defines
etcdhttp.Health
struct.

[endpoint]:[client-port]/health

etcdhttp.Health

Note that in v3.3.0-rc.0, v3.3.0-rc.1, and v3.3.0-rc.2,
etcdhttp.Health
has boolean type
"health"
and
"errors"
fields. For backward compatibilities, we reverted
"health"
field to
string
type and removed
"errors"
field. Further health information will be provided in separate APIs.

etcdhttp.Health

"health"

"errors"

"health"

string

"errors"

```
$ curl http://localhost:2379/health
{
"health"
:
"true"
}
```

#### Changed gRPC gateway HTTP endpoints (replaced
/v3alpha
with
/v3beta
)

/v3alpha

/v3beta

Before

```
curl -L http://localhost:2379/v3alpha/kv/put
\
-X POST -d
'{"key": "Zm9v", "value": "YmFy"}'
```

After

```
curl -L http://localhost:2379/v3beta/kv/put
\
-X POST -d
'{"key": "Zm9v", "value": "YmFy"}'
```

Requests to
/v3alpha
endpoints will redirect to
/v3beta
, and
/v3alpha
will be removed in 3.4 release.

/v3alpha

/v3beta

/v3alpha

#### Changed maximum request size limits

3.3 now allows custom request size limits for both server and
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

#### Changed raw gRPC client wrapper function signatures

3.3 changes the function signatures of
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

#### Changed clientv3
Snapshot
API error type

Snapshot

Previously, clientv3
Snapshot
API returned raw [
grpc/*status.statusError
] type error. v3.3 now translates those errors to corresponding public error types, to be consistent with other APIs.

Snapshot

grpc/*status.statusError

Before

```
import
"context"
// reading snapshot with canceled context should error out
ctx
,
cancel
:=
context
.
WithCancel
(
context
.
Background
())
rc
,
_
:=
cli
.
Snapshot
(
ctx
)
cancel
()
_
,
err
:=
io
.
Copy
(
f
,
rc
)
err
.
Error
()
==
"rpc error: code = Canceled desc = context canceled"
// reading snapshot with deadline exceeded should error out
ctx
,
cancel
=
context
.
WithTimeout
(
context
.
Background
(),
time
.
Second
)
defer
cancel
()
rc
,
_
=
cli
.
Snapshot
(
ctx
)
time
.
Sleep
(
2
*
time
.
Second
)
_
,
err
=
io
.
Copy
(
f
,
rc
)
err
.
Error
()
==
"rpc error: code = DeadlineExceeded desc = context deadline exceeded"
```

After

```
import
"context"
// reading snapshot with canceled context should error out
ctx
,
cancel
:=
context
.
WithCancel
(
context
.
Background
())
rc
,
_
:=
cli
.
Snapshot
(
ctx
)
cancel
()
_
,
err
:=
io
.
Copy
(
f
,
rc
)
err
==
context
.
Canceled
// reading snapshot with deadline exceeded should error out
ctx
,
cancel
=
context
.
WithTimeout
(
context
.
Background
(),
time
.
Second
)
defer
cancel
()
rc
,
_
=
cli
.
Snapshot
(
ctx
)
time
.
Sleep
(
2
*
time
.
Second
)
_
,
err
=
io
.
Copy
(
f
,
rc
)
err
==
context
.
DeadlineExceeded
```

#### Changed
etcdctl lease timetolive
command output

etcdctl lease timetolive

Previously,
lease timetolive LEASE_ID
command on expired lease prints
-1s
for remaining seconds. 3.3 now outputs clearer messages.

lease timetolive LEASE_ID

-1s

Before

```
lease 2d8257079fa1bc0c granted with TTL
(
0s
)
, remaining
(
-1s
)
```

After

```
lease 2d8257079fa1bc0c already expired
```

#### Changed
golang.org/x/net/context
imports

golang.org/x/net/context

clientv3
has deprecated
golang.org/x/net/context
. If a project vendors
golang.org/x/net/context
in other code (e.g. etcd generated protocol buffer code) and imports
github.com/coreos/etcd/clientv3
, it requires Go 1.9+ to compile.

clientv3

golang.org/x/net/context

github.com/coreos/etcd/clientv3

Before


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Upgrade etcd from 3.2 to 3.3](https://etcd.io/docs/v3.7/upgrades/upgrade_3_3/)
