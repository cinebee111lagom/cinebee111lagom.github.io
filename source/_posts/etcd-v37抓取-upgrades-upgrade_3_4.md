---
title: etcd v3.7 抓取：Upgrade etcd from 3.3 to 3.4
date: 2026-09-13 10:14:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/upgrades/upgrade_3_4/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/upgrades/upgrade_3_4/>

---

In the general case, upgrading from etcd 3.3 to 3.4 can be a zero-downtime, rolling upgrade:

one by one, stop the etcd v3.3 processes and replace them with etcd v3.4 processes

after running all v3.4 processes, new features in v3.4 are available to the cluster

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

Highlighted breaking changes in 3.4.

#### Make
ETCDCTL_API=3 etcdctl
default

ETCDCTL_API=3 etcdctl

ETCDCTL_API=3
is now the default.

ETCDCTL_API=3

```
etcdctl set foo bar
Error: unknown command "set" for "etcdctl"
-etcdctl set foo bar
+ETCDCTL_API=2 etcdctl set foo bar
bar
ETCDCTL_API=3 etcdctl put foo bar
OK
-ETCDCTL_API=3 etcdctl put foo bar
+etcdctl put foo bar
```

#### Make
etcd --enable-v2=false
default

etcd --enable-v2=false

etcd --enable-v2=false
is now the default.

etcd --enable-v2=false

This means, unless
etcd --enable-v2=true
is specified, etcd v3.4 server would not serve v2 API requests.

etcd --enable-v2=true

If v2 API were used, make sure to enable v2 API in v3.4:

```
-etcd
+etcd --enable-v2=true
```

Other HTTP APIs will still work (e.g.
[CLIENT-URL]/metrics
,
[CLIENT-URL]/health
, v3 gRPC gateway).

[CLIENT-URL]/metrics

[CLIENT-URL]/health

#### Deprecated
etcd --ca-file
and
etcd --peer-ca-file
flags

etcd --ca-file

etcd --peer-ca-file

--ca-file
and
--peer-ca-file
flags are deprecated; they have been deprecated since v2.1.

--ca-file

--peer-ca-file

Note setting this parameter will also automatically enable client cert authentication no matter what value is set for
--client-cert-auth
.

--client-cert-auth

```
-etcd --ca-file ca-client.crt
+etcd --trusted-ca-file ca-client.crt
```

```
-etcd --peer-ca-file ca-peer.crt
+etcd --peer-trusted-ca-file ca-peer.crt
```

#### Deprecated
grpc.ErrClientConnClosing
error

grpc.ErrClientConnClosing

grpc.ErrClientConnClosing
has been
deprecated in gRPC >= 1.10
.

grpc.ErrClientConnClosing

```
import (
+	"go.etcd.io/etcd/clientv3"
"google.golang.org/grpc"
+	"google.golang.org/grpc/codes"
+	"google.golang.org/grpc/status"
)
_, err := kvc.Get(ctx, "a")
-if err == grpc.ErrClientConnClosing {
+if clientv3.IsConnCanceled(err) {
// or
+s, ok := status.FromError(err)
+if ok {
+  if s.Code() == codes.Canceled
```

#### Require
grpc.WithBlock
for client dial

grpc.WithBlock

The new client balancer
uses an asynchronous resolver to pass endpoints to the gRPC dial function. As a result, v3.4 client requires
grpc.WithBlock
dial option to wait until the underlying connection is up.

grpc.WithBlock

```
import (
"time"
"go.etcd.io/etcd/clientv3"
+	"google.golang.org/grpc"
)
+// "grpc.WithBlock()" to block until the underlying connection is up
ccfg := clientv3.Config{
Endpoints:            []string{"localhost:2379"},
DialTimeout:          time.Second,
+ DialOptions:          []grpc.DialOption{grpc.WithBlock()},
DialKeepAliveTime:    time.Second,
DialKeepAliveTimeout: 500 * time.Millisecond,
}
```

#### Deprecating
etcd_debugging_mvcc_db_total_size_in_bytes
Prometheus metrics

etcd_debugging_mvcc_db_total_size_in_bytes

v3.4 promotes
etcd_debugging_mvcc_db_total_size_in_bytes
Prometheus metrics to
etcd_mvcc_db_total_size_in_bytes
, in order to encourage etcd storage monitoring.

etcd_debugging_mvcc_db_total_size_in_bytes

etcd_mvcc_db_total_size_in_bytes

etcd_debugging_mvcc_db_total_size_in_bytes
is still served in v3.4 for backward compatibilities. It will be completely deprecated in v3.5.

etcd_debugging_mvcc_db_total_size_in_bytes

```
-etcd_debugging_mvcc_db_total_size_in_bytes
+etcd_mvcc_db_total_size_in_bytes
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecating
etcd_debugging_mvcc_put_total
Prometheus metrics

etcd_debugging_mvcc_put_total

v3.4 promotes
etcd_debugging_mvcc_put_total
Prometheus metrics to
etcd_mvcc_put_total
, in order to encourage etcd storage monitoring.

etcd_debugging_mvcc_put_total

etcd_mvcc_put_total

etcd_debugging_mvcc_put_total
is still served in v3.4 for backward compatibilities. It will be completely deprecated in v3.5.

etcd_debugging_mvcc_put_total

```
-etcd_debugging_mvcc_put_total
+etcd_mvcc_put_total
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecating
etcd_debugging_mvcc_delete_total
Prometheus metrics

etcd_debugging_mvcc_delete_total

v3.4 promotes
etcd_debugging_mvcc_delete_total
Prometheus metrics to
etcd_mvcc_delete_total
, in order to encourage etcd storage monitoring.

etcd_debugging_mvcc_delete_total

etcd_mvcc_delete_total

etcd_debugging_mvcc_delete_total
is still served in v3.4 for backward compatibilities. It will be completely deprecated in v3.5.

etcd_debugging_mvcc_delete_total

```
-etcd_debugging_mvcc_delete_total
+etcd_mvcc_delete_total
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecating
etcd_debugging_mvcc_txn_total
Prometheus metrics

etcd_debugging_mvcc_txn_total

v3.4 promotes
etcd_debugging_mvcc_txn_total
Prometheus metrics to
etcd_mvcc_txn_total
, in order to encourage etcd storage monitoring.

etcd_debugging_mvcc_txn_total

etcd_mvcc_txn_total

etcd_debugging_mvcc_txn_total
is still served in v3.4 for backward compatibilities. It will be completely deprecated in v3.5.

etcd_debugging_mvcc_txn_total

```
-etcd_debugging_mvcc_txn_total
+etcd_mvcc_txn_total
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecating
etcd_debugging_mvcc_range_total
Prometheus metrics

etcd_debugging_mvcc_range_total

v3.4 promotes
etcd_debugging_mvcc_range_total
Prometheus metrics to
etcd_mvcc_range_total
, in order to encourage etcd storage monitoring.

etcd_debugging_mvcc_range_total

etcd_mvcc_range_total

etcd_debugging_mvcc_range_total
is still served in v3.4 for backward compatibilities. It will be completely deprecated in v3.5.

etcd_debugging_mvcc_range_total

```
-etcd_debugging_mvcc_range_total
+etcd_mvcc_range_total
```

Note that
etcd_debugging_*
namespace metrics have been marked as experimental. As we improve monitoring guide, we may promote more metrics.

etcd_debugging_*

#### Deprecating
etcd --log-output
flag (now
--log-outputs
)

etcd --log-output

--log-outputs

Rename
etcd --log-output
to
--log-outputs
to support multiple log outputs.
etcd --logger=capnslog
does not support multiple log outputs.

etcd --log-output

--log-outputs

etcd --logger=capnslog

etcd --log-output
will be deprecated in v3.5.
etcd --logger=capnslog
will be deprecated in v3.5
.

etcd --log-output

etcd --logger=capnslog

```
-etcd --log-output=stderr
+etcd --log-outputs=stderr
+# to write logs to stderr and a.log file at the same time
+# only "--logger=zap" supports multiple writers
+etcd --logger=zap --log-outputs=stderr,a.log
```

v3.4 adds
etcd --logger=zap --log-outputs=stderr
support for structured logging and multiple log outputs. Main motivation is to promote automated etcd monitoring, rather than looking back server logs when it starts breaking. Future development will make etcd log as few as possible, and make etcd easier to monitor with metrics and alerts.
etcd --logger=capnslog
will be deprecated in v3.5
.

etcd --logger=zap --log-outputs=stderr

etcd --logger=capnslog

#### Changed
log-outputs
field type in
etcd --config-file
to
[]string

log-outputs

etcd --config-file

[]string

Now that
log-outputs
(old field name
log-output
) accepts multiple writers, etcd configuration YAML file
log-outputs
field must be changed to
[]string
type as below:

log-outputs

log-output

log-outputs

[]string

```
# Specify 'stdout' or 'stderr' to skip journald logging even when running under systemd.
-log-output: default
+log-outputs: [default]
```

#### Renamed
embed.Config.LogOutput
to
embed.Config.LogOutputs

embed.Config.LogOutput

embed.Config.LogOutputs

Renamed
embed.Config.LogOutput
to
embed.Config.LogOutputs
to support multiple log outputs. And changed
embed.Config.LogOutput
type from
string
to
[]string
to support multiple log outputs.

embed.Config.LogOutput

embed.Config.LogOutputs

embed.Config.LogOutput

string

[]string

```
import "github.com/coreos/etcd/embed"
cfg := &embed.Config{Debug: false}
-cfg.LogOutput = "stderr"
+cfg.LogOutputs = []string{"stderr"}
```

#### v3.5 deprecates
capnslog

capnslog

v3.5 will deprecate
etcd --log-package-levels
flag for
capnslog
;
etcd --logger=zap --log-outputs=stderr
will the default.
v3.5 will deprecate
[CLIENT-URL]/config/local/log
endpoint.

etcd --log-package-levels

capnslog

etcd --logger=zap --log-outputs=stderr

[CLIENT-URL]/config/local/log

```
-etcd
+etcd --logger zap
```

#### Deprecating
etcd --debug
flag (now
--log-level=debug
)

etcd --debug

--log-level=debug

v3.4 deprecates
etcd --debug
flag. Instead, use
etcd --log-level=debug
flag.

etcd --debug

etcd --log-level=debug

```
-etcd --debug
+etcd --logger zap --log-level debug
```

#### Deprecated
pkg/transport.TLSInfo.CAFile
field

pkg/transport.TLSInfo.CAFile

Deprecated
pkg/transport.TLSInfo.CAFile
field.

pkg/transport.TLSInfo.CAFile

```
import "github.com/coreos/etcd/pkg/transport"
tlsInfo := transport.TLSInfo{
CertFile: "/tmp/test-certs/test.pem",
KeyFile: "/tmp/test-certs/test-key.pem",
-   CAFile: "/tmp/test-certs/trusted-ca.pem",
+   TrustedCAFile: "/tmp/test-certs/trusted-ca.pem",
}
tlsConfig, err := tlsInfo.ClientConfig()
if err != nil {
panic(err)
}
```

#### Changed
embed.Config.SnapCount
to
embed.Config.SnapshotCount

embed.Config.SnapCount

embed.Config.SnapshotCount

To be consistent with the flag name
etcd --snapshot-count
,
embed.Config.SnapCount
field has been renamed to
embed.Config.SnapshotCount
:

etcd --snapshot-count

embed.Config.SnapCount

embed.Config.SnapshotCount

```
import "github.com/coreos/etcd/embed"
cfg := embed.NewConfig()
-cfg.SnapCount = 100000
+cfg.SnapshotCount = 100000
```

#### Changed
etcdserver.ServerConfig.SnapCount
to
etcdserver.ServerConfig.SnapshotCount

etcdserver.ServerConfig.SnapCount

etcdserver.ServerConfig.SnapshotCount

To be consistent with the flag name
etcd --snapshot-count
,
etcdserver.ServerConfig.SnapCount
field has been renamed to
etcdserver.ServerConfig.SnapshotCount
:

etcd --snapshot-count

etcdserver.ServerConfig.SnapCount

etcdserver.ServerConfig.SnapshotCount

```
import "github.com/coreos/etcd/etcdserver"
srvcfg := etcdserver.ServerConfig{
-  SnapCount: 100000,
+  SnapshotCount: 100000,
```

#### Changed function signature in package
wal

wal

Changed
wal
function signatures to support structured logger.

wal

```
import "github.com/coreos/etcd/wal"
+import "go.uber.org/zap"
+lg, _ = zap.NewProduction()
-wal.Open(dirpath, snap)
+wal.Open(lg, dirpath, snap)
-wal.OpenForRead(dirpath, snap)
+wal.OpenForRead(lg, dirpath, snap)
-wal.Repair(dirpath)
+wal.Repair(lg, dirpath)
-wal.Create(dirpath, metadata)
+wal.Create(lg, dirpath, metadata)
```

#### Changed
IntervalTree
type in package
pkg/adt

IntervalTree

pkg/adt

pkg/adt.IntervalTree
is now defined as an
interface
.

pkg/adt.IntervalTree

interface

```
import (
"fmt"
"go.etcd.io/etcd/pkg/adt"
)
func main() {
-    ivt := &adt.IntervalTree{}
+    ivt := adt.NewIntervalTree()
```


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Upgrade etcd from 3.3 to 3.4](https://etcd.io/docs/v3.7/upgrades/upgrade_3_4/)
