---
title: etcd v3.7 抓取：Golang modules
date: 2026-09-13 10:37:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/dev-internal/modules/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/dev-internal/modules/>

---

The etcd project (since version 3.5) is organized into multiple
golang modules
hosted in a
single repository
.

There are following modules:

go.etcd.io/etcd/api/v3
- contains API definitions
(like protos & proto-generated libraries) that defines communication protocol
between etcd clients and server.

go.etcd.io/etcd/pkg/v3
- collection of utility packages used by etcd
without being specific to etcd itself. A package belongs here
only if it could possibly be moved out into its own repository in the future.
Please avoid adding here code that has a lot of dependencies on its own, as
they automatically becoming dependencies of the client library
(that we want to keep lightweight).

go.etcd.io/etcd/client/v3
- client library used to contact etcd over
the network (grpc). Recommended for all new usage of etcd.

go.etcd.io/etcd/client/v2
- legacy client library used to contact etcd
over HTTP protocol. Deprecated. All new usage should depend on /v3 library.

go.etcd.io/etcd/raft/v3
- implementation of distributed consensus
protocol. Should have no etcd specific code.

go.etcd.io/etcd/server/v3
- etcd implementation.
The code in this package is etcd internal and should not be consumed
by external projects. The package layout and API can change within the minor versions.

go.etcd.io/etcd/etcdctl/v3
- a command line tool to access and manage etcd.

go.etcd.io/etcd/tests/v3
- a module that contains all integration tests of etcd.
Notice: All unit-tests (fast and not requiring cross-module dependencies)
should be kept in the local modules to the code under the test.

go.etcd.io/bbolt
- implementation of persistent b-tree.
Hosted in a separate repository:
https://github.com/etcd-io/bbolt
.

### Operations

All etcd modules should be released in the same versions, e.g.
go.etcd.io/etcd/client/v3@v3.5.10
must depend on
go.etcd.io/etcd/api/v3@v3.5.10
.
The consistent updating of versions can by performed using:
%
DRY_RUN
=
false
TARGET_VERSION
=
"v3.5.10"
./scripts/release_mod.sh update_versions

All etcd modules should be released in the same versions, e.g.
go.etcd.io/etcd/client/v3@v3.5.10
must depend on
go.etcd.io/etcd/api/v3@v3.5.10
.

go.etcd.io/etcd/client/v3@v3.5.10

go.etcd.io/etcd/api/v3@v3.5.10

The consistent updating of versions can by performed using:

```
%
DRY_RUN
=
false
TARGET_VERSION
=
"v3.5.10"
./scripts/release_mod.sh update_versions
```

The released modules should be tagged according to
https://golang.org/ref/mod#vcs-version
rules,
i.e. each module should get its own tag.
The tagging can be performed using:
%
DRY_RUN
=
false
REMOTE_REPO
=
"origin"
./scripts/release_mod.sh push_mod_tags

The released modules should be tagged according to
https://golang.org/ref/mod#vcs-version
rules,
i.e. each module should get its own tag.
The tagging can be performed using:

```
%
DRY_RUN
=
false
REMOTE_REPO
=
"origin"
./scripts/release_mod.sh push_mod_tags
```

All etcd modules should depend on the same versions of underlying dependencies.
This can be verified using:
%
PASSES
=
"dep"
./test.sh

All etcd modules should depend on the same versions of underlying dependencies.
This can be verified using:

```
%
PASSES
=
"dep"
./test.sh
```

The go.mod files must not contain dependencies not being used and must
conform to
go mod tidy
format.
This is being verified by:
% PASSES="mod_tidy" ./test.sh

The go.mod files must not contain dependencies not being used and must
conform to
go mod tidy
format.
This is being verified by:

go mod tidy

```
% PASSES="mod_tidy" ./test.sh
```

To trigger actions across all modules (e.g. auto-format all files), please
use/expand the following script:
% ./scripts/fix.sh

To trigger actions across all modules (e.g. auto-format all files), please
use/expand the following script:

```
% ./scripts/fix.sh
```

### Future

As a North Star, we would like to evaluate etcd modules towards following model:

This assumes:

Splitting etcdmigrate/etcdadm out of etcdctl binary.
Thanks to this etcdctl would become clearly a command-line wrapper
around network client API,
while etcdmigrate/etcdadm would support direct physical operations on the
etcd storage files.

Splitting etcd-proxy out of ./etcd binary, as it contains more experimental code
so carries additional risk & dependencies.

Deprecation of support for v2 protocol.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Golang modules](https://etcd.io/docs/v3.7/dev-internal/modules/)
