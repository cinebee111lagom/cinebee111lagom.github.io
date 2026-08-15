---
title: etcd v3.7 抓取：etcd versus other key-value stores
date: 2026-09-13 10:06:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/learning/why/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/learning/why/>

---

The name “etcd” originated from two ideas, the unix “/etc” folder and “d"istributed systems. The “/etc” folder is a place to store configuration data for a single system whereas etcd stores configuration information for large scale distributed systems. Hence, a “d"istributed “/etc” is “etcd”.

etcd is designed as a general substrate for large scale distributed systems. These are systems that will never tolerate split-brain operation and are willing to sacrifice availability to achieve this end. etcd stores metadata in a consistent and fault-tolerant way. An etcd cluster is meant to provide key-value storage with best of class stability, reliability, scalability and performance.

Distributed systems use etcd as a consistent key-value store for configuration management, service discovery, and coordinating distributed work. Many
organizations
use etcd to implement production systems such as container schedulers, service discovery services, and distributed data storage. Common distributed patterns using etcd include
leader election
,
distributed locks
, and monitoring machine liveness.

## Use cases

Container Linux by CoreOS: Applications running on
Container Linux
get automatic, zero-downtime Linux kernel updates. Container Linux uses
locksmith
to coordinate updates. Locksmith implements a distributed semaphore over etcd to ensure only a subset of a cluster is rebooting at any given time.

Kubernetes
stores configuration data into etcd for service discovery and cluster management; etcd’s consistency is crucial for correctly scheduling and operating services. The Kubernetes API server persists cluster state into etcd. It uses etcd’s watch API to monitor the cluster and roll out critical configuration changes.

## Comparison chart

Perhaps etcd already seems like a good fit, but as with all technological decisions, proceed with caution. Please note this documentation is written by the etcd team. Although the ideal is a disinterested comparison of technology and features, the authors’ expertise and biases obviously favor etcd. Use only as directed.

The table below is a handy quick reference for spotting the differences among etcd and its most popular alternatives at a glance. Further commentary and details for each column are in the sections following the table.

### ZooKeeper

ZooKeeper solves the same problem as etcd: distributed system coordination and metadata storage. However, etcd has the luxury of hindsight taken from engineering and operational experience with ZooKeeper’s design and implementation. The lessons learned from Zookeeper certainly informed etcd’s design, helping it support large scale systems like Kubernetes. The improvements etcd made over Zookeeper include:

Dynamic cluster membership reconfiguration

Stable read/write under high load

A multi-version concurrency control data model

Reliable key monitoring which never silently drop events

Lease primitives decoupling connections from sessions

APIs for safe distributed shared locks

Furthermore, etcd supports a wide range of languages and frameworks out of the box. Whereas Zookeeper has its own custom Jute RPC protocol, which is totally unique to Zookeeper and limits its
supported language bindings
, etcd’s client protocol is built from
gRPC
, a popular RPC framework with language bindings for go, C++, Java, and more. Likewise, gRPC can be serialized into JSON over HTTP, so even general command line utilities like
curl
can talk to it. Since systems can select from a variety of choices, they are built on etcd with native tooling rather than around etcd with a single fixed set of technologies.

curl

When considering features, support, and stability, new applications planning to use Zookeeper for a consistent key value store would do well to choose etcd instead.

### Consul

Consul is an end-to-end service discovery framework. It provides built-in health checking, failure detection, and DNS services. In addition, Consul exposes a key value store with RESTful HTTP APIs.
As it stands in Consul 1.0
, the storage system does not scale as well as other systems like etcd or Zookeeper in key-value operations; systems requiring millions of keys will suffer from high latencies and memory pressure. The key value API is missing, most notably, multi-version keys, conditional transactions, and reliable streaming watches.

etcd and Consul solve different problems. If looking for a distributed consistent key value store, etcd is a better choice over Consul. If looking for end-to-end cluster service discovery, etcd will not have enough features; choose Kubernetes, Consul, or SmartStack.

### NewSQL (Cloud Spanner, CockroachDB, TiDB)

Both etcd and NewSQL databases (e.g.,
Cockroach
,
TiDB
,
Google Spanner
) provide strong data consistency guarantees with high availability. However, the significantly different system design parameters lead to significantly different client APIs and performance characteristics.

NewSQL databases are meant to horizontally scale across data centers. These systems typically partition data across multiple consistent replication groups (shards), potentially distant, storing data sets on the order of terabytes and above. This sort of scaling makes them poor candidates for distributed coordination as they have long latencies from waiting on clocks and expect updates with mostly localized dependency graphs. The data is organized into tables, including SQL-style query facilities with richer semantics than etcd, but at the cost of additional complexity for processing, planning, and optimizing queries.

In short, choose etcd for storing metadata or coordinating distributed applications. If storing more than a few GB of data or if full SQL queries are needed, choose a NewSQL database.

## Using etcd for metadata

etcd replicates all data within a single consistent replication group. For storing up to a few GB of data with consistent ordering, this is the most efficient approach. Each modification of cluster state, which may change multiple keys, is assigned a global unique ID, called a revision in etcd, from a monotonically increasing counter for reasoning over ordering. Since there’s only a single replication group, the modification request only needs to go through the raft protocol to commit. By limiting consensus to one replication group, etcd gets distributed consistency with a simple protocol while achieving low latency and high throughput.

The replication behind etcd cannot horizontally scale because it lacks data sharding. In contrast, NewSQL databases usually shard data across multiple consistent replication groups, storing data sets on the order of terabytes and above. However, to assign each modification a global unique and increasing ID, each request must go through an additional coordination protocol among replication groups. This extra coordination step may potentially conflict on the global ID, forcing ordered requests to retry. The result is a more complicated approach with typically worse performance than etcd for strict ordering.

If an application reasons primarily about metadata or metadata ordering, such as to coordinate processes, choose etcd. If the application needs a large data store spanning multiple data centers and does not heavily depend on strong global ordering properties, choose a NewSQL database.

## Using etcd for distributed coordination

etcd has distributed coordination primitives such as event watches, leases, elections, and distributed shared locks out of the box (Note that in the case of the distributed shared lock, users need to be aware about its non obvious properties. The details are described below). These primitives are both maintained and supported by the etcd developers; leaving these primitives to external libraries shirks the responsibility of developing foundational distributed software, essentially leaving the system incomplete. NewSQL databases usually expect these distributed coordination primitives to be authored by third parties. Likewise, ZooKeeper famously has a separate and independent
library
of coordination recipes. Consul, which provides a native locking API, goes so far as to apologize that it’s “
not a bulletproof method
”.

In theory, it’s possible to build these primitives atop any storage systems providing strong consistency. However, the algorithms tend to be subtle; it is easy to develop a locking algorithm that appears to work, only to suddenly break due to thundering herd and timing skew. Furthermore, other primitives supported by etcd, such as transactional memory depend on etcd’s MVCC data model; simple strong consistency is not enough.

For distributed coordination, choosing etcd can help prevent operational headaches and save engineering effort.

### Notes on the usage of lock and lease

etcd provides
lock APIs
which are based on
the lease mechanism
and
its implementation in etcd
. The basic idea of the lease mechanism is: a server grants a token, which is called a lease, to a requesting client. When the server grants a lease, it associates a TTL with the lease. When the server detects the passage of time longer than the TTL, it revokes the lease. While the client holds a non revoked lease it can claim that it owns access to a resource associated with the lease. In the case of etcd, the resource is a key in the etcd keyspace. etcd provides lock APIs with this scheme. However, the lock APIs cannot be used as mutual exclusion mechanism by themselves. The APIs are called lock because
for historical reasons
. The lock APIs can, however, be used as an optimization mechanism of mutual exclusion as described below.

The most important aspect of the lease mechanism is that TTL is defined as a physical time interval. Both of the server and client measures passing of time with their own clocks. It allows a situation that the server revokes the lease but the client still claims it owns the lease.

Then how does the lease mechanism guarantees mutual exclusion of the locking mechanism? Actually, the lease mechanism itself doesn’t guarantee mutual exclusion. Owning a lease cannot guarantee the owner holds a lock of the resource.

In the case of controlling mutual accesses to keys of etcd itself with etcd lock, mutual exclusion is implemented based on the mechanism of version number validation (it is sometimes called compare and swap in other systems like Consul). In etcd’s RPCs like
Put
or
Txn
, we can specify required conditions about revision number and lease ID for the operations. If the conditions are not satisfied, the operation can fail. With this mechanism, etcd provides distributed locking for clients. It means that a client knows that it is acquiring a lock of a key when its requests are completed by etcd cluster successfully.

Put

Txn

In distributed locking literature similar designs are described:

In
the paper of Chubby
, the concept of
sequencer
is introduced. We interpret that sequencer is an almost same to the combination of revision number and lease ID of etcd.

In
How to do distributed locking
, Martin Kleppmann introduced the idea of
fencing token
. The authors interpret that fencing token is revision number in the case of etcd.

In
Practical Uses of Synchronized Clocks in Distributed Systems
, we can find a description that Thor implements a distributed locking mechanism based on version number validation and lease.

Why do etcd and other systems provide lease if they provide mutual exclusion based on version number validation? Well, leases provide an optimization mechanism for reducing a number of aborted requests.

Note that in the case of etcd keys, it can be locked efficiently because of the mechanisms of lease and version number validation. If users need to protect resources which aren’t related to etcd, the resources must provide the version number validation mechanism and consistency of replicas like keys of etcd. The lock feature of etcd itself cannot be used for protecting external resources.

## Feedback


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[etcd versus other key-value stores](https://etcd.io/docs/v3.7/learning/why/)
