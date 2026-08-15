---
title: etcd v3.7 抓取：Set up a local cluster
date: 2026-09-13 09:49:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/dev-guide/local_cluster/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/dev-guide/local_cluster/>

---

For testing and development deployments, the quickest and easiest way is to configure a local cluster. For a production deployment, refer to the
clustering
section.

## Local standalone cluster

### Starting a cluster

Run the following to deploy an etcd cluster as a standalone cluster:

```
$ ./etcd
...
```

If the
etcd
binary is not present in the current working directory, it might be located either at
$GOPATH/bin/etcd
or at
/usr/local/bin/etcd
. Run the command appropriately.

etcd

$GOPATH/bin/etcd

/usr/local/bin/etcd

The running etcd member listens on
localhost:2379
for client requests.

localhost:2379

### Interacting with the cluster

Use
etcdctl
to interact with the running cluster:

etcdctl

Store an example key-value pair in the cluster:
$ ./etcdctl put foo bar
  OK
If OK is printed, storing key-value pair is successful.

Store an example key-value pair in the cluster:

```
$ ./etcdctl put foo bar
  OK
```

If OK is printed, storing key-value pair is successful.

Retrieve the value of
foo
:
$ ./etcdctl get foo
bar
If
bar
is returned, interaction with the etcd cluster is working as expected.

Retrieve the value of
foo
:

foo

```
$ ./etcdctl get foo
bar
```

If
bar
is returned, interaction with the etcd cluster is working as expected.

bar

## Local multi-member cluster

### Starting a cluster

A
Procfile
at the base of the etcd git repository is provided to easily configure a local multi-member cluster. To start a multi-member cluster, navigate to the root of the etcd source tree and perform the following:

Procfile

Install
goreman
to control Procfile-based applications:
$ go install github.com/mattn/goreman@latest

Install
goreman
to control Procfile-based applications:

goreman

```
$ go install github.com/mattn/goreman@latest
```

Start a cluster with
goreman
using etcd’s stock Procfile:
$ goreman -f Procfile start
The members start running. They listen on
localhost:2379
,
localhost:22379
, and
localhost:32379
respectively for client requests.

Start a cluster with
goreman
using etcd’s stock Procfile:

goreman

```
$ goreman -f Procfile start
```

The members start running. They listen on
localhost:2379
,
localhost:22379
, and
localhost:32379
respectively for client requests.

localhost:2379

localhost:22379

localhost:32379

### Interacting with the cluster

Use
etcdctl
to interact with the running cluster:

etcdctl

Print the list of members:
$ etcdctl --write-out=table --endpoints=localhost:2379 member list
The list of etcd members are displayed as follows:
+------------------+---------+--------+------------------------+------------------------+
|        ID        | STATUS  |  NAME  |       PEER ADDRS       |      CLIENT ADDRS      |
+------------------+---------+--------+------------------------+------------------------+
| 8211f1d0f64f3269 | started | infra1 | http://127.0.0.1:2380  | http://127.0.0.1:2379  |
| 91bc3c398fb3c146 | started | infra2 | http://127.0.0.1:22380 | http://127.0.0.1:22379 |
| fd422379fda50e48 | started | infra3 | http://127.0.0.1:32380 | http://127.0.0.1:32379 |
+------------------+---------+--------+------------------------+------------------------+

Print the list of members:

```
$ etcdctl --write-out=table --endpoints=localhost:2379 member list
```

The list of etcd members are displayed as follows:

```
+------------------+---------+--------+------------------------+------------------------+
|        ID        | STATUS  |  NAME  |       PEER ADDRS       |      CLIENT ADDRS      |
+------------------+---------+--------+------------------------+------------------------+
| 8211f1d0f64f3269 | started | infra1 | http://127.0.0.1:2380  | http://127.0.0.1:2379  |
| 91bc3c398fb3c146 | started | infra2 | http://127.0.0.1:22380 | http://127.0.0.1:22379 |
| fd422379fda50e48 | started | infra3 | http://127.0.0.1:32380 | http://127.0.0.1:32379 |
+------------------+---------+--------+------------------------+------------------------+
```

Store an example key-value pair in the cluster:
$ etcdctl put foo bar
OK
If OK is printed, storing key-value pair is successful.

Store an example key-value pair in the cluster:

```
$ etcdctl put foo bar
OK
```

If OK is printed, storing key-value pair is successful.

### Testing fault tolerance

To exercise etcd’s fault tolerance, kill a member and attempt to retrieve the key.

Identify the process name of the member to be stopped.
The
Procfile
lists the properties of the multi-member cluster. For example, consider the member with the process name,
etcd2
.

Identify the process name of the member to be stopped.

The
Procfile
lists the properties of the multi-member cluster. For example, consider the member with the process name,
etcd2
.

Procfile

etcd2

Stop the member:
# kill etcd2
$ goreman run stop etcd2

Stop the member:

```
# kill etcd2
$ goreman run stop etcd2
```

Store a key:
$ etcdctl put key hello
OK

Store a key:

```
$ etcdctl put key hello
OK
```

Retrieve the key that is stored in the previous step:
$ etcdctl get key
hello

Retrieve the key that is stored in the previous step:

```
$ etcdctl get key
hello
```

Retrieve a key from the stopped member:
$ etcdctl --endpoints=localhost:22379 get key
The command should display an error caused by connection failure:
2017/06/18 23:07:35 grpc: Conn.resetTransport failed to create client transport: connection error: desc = "transport: dial tcp 127.0.0.1:22379: getsockopt: connection refused"; Reconnecting to "localhost:22379"
Error:  grpc: timed out trying to connect

Retrieve a key from the stopped member:

```
$ etcdctl --endpoints=localhost:22379 get key
```

The command should display an error caused by connection failure:

```
2017/06/18 23:07:35 grpc: Conn.resetTransport failed to create client transport: connection error: desc = "transport: dial tcp 127.0.0.1:22379: getsockopt: connection refused"; Reconnecting to "localhost:22379"
Error:  grpc: timed out trying to connect
```

Restart the stopped member:
$ goreman run restart etcd2

Restart the stopped member:

```
$ goreman run restart etcd2
```

Get the key from the restarted member:
$ etcdctl --endpoints=localhost:22379 get key
hello
Restarting the member re-establish the connection.
etcdctl
will now be able to retrieve the key successfully. To learn more about interacting with etcd, read
interacting with etcd section
.

Get the key from the restarted member:

```
$ etcdctl --endpoints=localhost:22379 get key
hello
```

Restarting the member re-establish the connection.
etcdctl
will now be able to retrieve the key successfully. To learn more about interacting with etcd, read
interacting with etcd section
.

etcdctl

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Set up a local cluster](https://etcd.io/docs/v3.7/dev-guide/local_cluster/)
