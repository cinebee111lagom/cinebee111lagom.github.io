---
title: etcd v3.7 抓取：FAQ
date: 2026-09-13 09:04:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/faq/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/faq/>

---

## etcd, general

### What is etcd?

etcd is a consistent distributed key-value store. Mainly used as a separate coordination service, in distributed systems. And designed to hold small amounts of data that can fit entirely in memory.

### How do you pronounce etcd?

etcd is pronounced
/ˈɛtsiːdiː/
, and means “distributed
etc
directory.”

etc

### Do clients have to send requests to the etcd leader?

Raft
is leader-based; the leader handles all client requests which need cluster consensus. However, the client does not need to know which node is the leader. Any request that requires consensus sent to a follower is automatically forwarded to the leader. Requests that do not require consensus (e.g., serialized reads) can be processed by any cluster member.

## Configuration

### What is the difference between listen-<client,peer>-urls, advertise-client-urls or initial-advertise-peer-urls?

listen-client-urls
and
listen-peer-urls
specify the local addresses etcd server binds to for accepting incoming connections. To listen on a port for all interfaces, specify
0.0.0.0
as the listen IP address.

listen-client-urls

listen-peer-urls

0.0.0.0

advertise-client-urls
and
initial-advertise-peer-urls
specify the addresses etcd clients or other etcd members should use to contact the etcd server. The advertise addresses must be reachable from the remote machines. Do not advertise addresses like
localhost
or
0.0.0.0
for a production setup since these addresses are unreachable from remote machines.

advertise-client-urls

initial-advertise-peer-urls

localhost

0.0.0.0

### Why doesn’t changing
--listen-peer-urls
or
--initial-advertise-peer-urls
update the advertised peer URLs in
etcdctl member list
?

--listen-peer-urls

--initial-advertise-peer-urls

etcdctl member list

A member’s advertised peer URLs come from
--initial-advertise-peer-urls
on initial cluster boot. Changing the listen peer URLs or the initial advertise peers after booting the member won’t affect the exported advertise peer URLs since changes must go through quorum to avoid membership configuration split brain. Use
etcdctl member update
to update a member’s peer URLs.

--initial-advertise-peer-urls

etcdctl member update

## Deployment

### System requirements

Since etcd writes data to disk, its performance strongly depends on disk performance. For this reason, SSD is highly recommended. To assess whether a disk is fast enough for etcd, one possibility is using a disk benchmarking tool such as
fio
. For an example on how to do that, read
here
. To prevent performance degradation or unintentionally overloading the key-value store, etcd enforces a configurable storage size quota set to 2GB by default. To avoid swapping or running out of memory, the machine should have at least as much RAM to cover the quota. 8GB is a suggested maximum size for normal environments and etcd warns at startup if the configured value exceeds it. At CoreOS, an etcd cluster is usually deployed on dedicated CoreOS Container Linux machines with dual-core processors, 2GB of RAM, and 80GB of SSD
at the very least
.
Note that performance is intrinsically workload dependent; please test before production deployment
. See
hardware
for more recommendations.

Most stable production environment is Linux operating system with amd64 architecture; see
supported platform
for more.

### Why an odd number of cluster members?

An etcd cluster needs a majority of nodes, a quorum, to agree on updates to the cluster state. For a cluster with n members, quorum is (n/2)+1. For any odd-sized cluster, adding one node will always increase the number of nodes necessary for quorum. Although adding a node to an odd-sized cluster appears better since there are more machines, the fault tolerance is worse since exactly the same number of nodes may fail without losing quorum but there are more nodes that can fail. If the cluster is in a state where it can’t tolerate any more failures, adding a node before removing nodes is dangerous because if the new node fails to register with the cluster (e.g., the address is misconfigured), quorum will be permanently lost.

### What is maximum cluster size?

Theoretically, there is no hard limit. However, an etcd cluster probably should have no more than seven nodes.
Google Chubby lock service
, similar to etcd and widely deployed within Google for many years, suggests running five nodes. A 5-member etcd cluster can tolerate two member failures, which is enough in most cases. Although larger clusters provide better fault tolerance, the write performance suffers because data must be replicated across more machines.

### What is failure tolerance?

An etcd cluster operates so long as a member quorum can be established. If quorum is lost through transient network failures (e.g., partitions), etcd automatically and safely resumes once the network recovers and restores quorum; Raft enforces cluster consistency. For power loss, etcd persists the Raft log to disk; etcd replays the log to the point of failure and resumes cluster participation. For permanent hardware failure, the node may be removed from the cluster through
runtime reconfiguration
.

It is recommended to have an odd number of members in a cluster. An odd-size cluster tolerates the same number of failures as an even-size cluster but with fewer nodes. The difference can be seen by comparing even and odd sized clusters:

Adding a member to bring the size of cluster up to an even number doesn’t buy additional fault tolerance. Likewise, during a network partition, an odd number of members guarantees that there will always be a majority partition that can continue to operate and be the source of truth when the partition ends.

### Does etcd work in cross-region or cross data center deployments?

Deploying etcd across regions improves etcd’s fault tolerance since members are in separate failure domains. The cost is higher consensus request latency from crossing data center boundaries. Since etcd relies on a member quorum for consensus, the latency from crossing data centers will be somewhat pronounced because at least a majority of cluster members must respond to consensus requests. Additionally, cluster data must be replicated across all peers, so there will be bandwidth cost as well.

With longer latencies, the default etcd configuration may cause frequent elections or heartbeat timeouts. See
tuning
for adjusting timeouts for high latency deployments.

## Operation

### How to backup a etcd cluster?

etcdctl provides a
snapshot
command to create backups. See
backup
for more details.

snapshot

### Should I add a member before removing an unhealthy member?

When replacing an etcd node, it’s important to remove the member first and then add its replacement.

etcd employs distributed consensus based on a quorum model; (n/2)+1 members, a majority, must agree on a proposal before it can be committed to the cluster. These proposals include key-value updates and membership changes. This model totally avoids any possibility of split brain inconsistency. The downside is permanent quorum loss is catastrophic.

How this applies to membership: If a 3-member cluster has 1 downed member, it can still make forward progress because the quorum is 2 and 2 members are still live. However, adding a new member to a 3-member cluster will increase the quorum to 3 because 3 votes are required for a majority of 4 members. Since the quorum increased, this extra member buys nothing in terms of fault tolerance; the cluster is still one node failure away from being unrecoverable.

Additionally, that new member is risky because it may turn out to be misconfigured or incapable of joining the cluster. In that case, there’s no way to recover quorum because the cluster has two members down and two members up, but needs three votes to change membership to undo the botched membership addition. etcd will by default reject member add attempts that could take down the cluster in this manner.

On the other hand, if the downed member is removed from cluster membership first, the number of members becomes 2 and the quorum remains at 2. Following that removal by adding a new member will also keep the quorum steady at 2. So, even if the new node can’t be brought up, it’s still possible to remove the new member through quorum on the remaining live members.

### Why won’t etcd accept my membership changes?

etcd sets
strict-reconfig-check
in order to reject reconfiguration requests that would cause quorum loss. Abandoning quorum is really risky (especially when the cluster is already unhealthy). Although it may be tempting to disable quorum checking if there’s quorum loss to add a new member, this could lead to full fledged cluster inconsistency. For many applications, this will make the problem even worse (“disk geometry corruption” being a candidate for most terrifying).

strict-reconfig-check

### Why does etcd lose its leader from disk latency spikes?

This is intentional; disk latency is part of leader liveness. Suppose the cluster leader takes a minute to fsync a raft log update to disk, but the etcd cluster has a one second election timeout. Even though the leader can process network messages within the election interval (e.g., send heartbeats), it’s effectively unavailable because it can’t commit any new proposals; it’s waiting on the slow disk. If the cluster frequently loses its leader due to disk latencies, try
tuning
the disk settings or etcd time parameters.

### What does the etcd warning “request ignored (cluster ID mismatch)” mean?

Every new etcd cluster generates a new cluster ID based on the initial cluster configuration and a user-provided unique
initial-cluster-token
value. By having unique cluster ID’s, etcd is protected from cross-cluster interaction which could corrupt the cluster.

initial-cluster-token

Usually this warning happens after tearing down an old cluster, then reusing some of the peer addresses for the new cluster. If any etcd process from the old cluster is still running it will try to contact the new cluster. The new cluster will recognize a cluster ID mismatch, then ignore the request and emit this warning. This warning is often cleared by ensuring peer addresses among distinct clusters are disjoint.

### What does “mvcc: database space exceeded” mean and how do I fix it?

The
multi-version concurrency control
data model in etcd keeps an exact history of the keyspace. Without periodically compacting this history (e.g., by setting
--auto-compaction
), etcd will eventually exhaust its storage space. If etcd runs low on storage space, it raises a space quota alarm to protect the cluster from further writes. So long as the alarm is raised, etcd responds to write requests with the error
mvcc: database space exceeded
.

--auto-compaction

mvcc: database space exceeded

To recover from the low space quota alarm:

Compact
etcd’s history.

Defragment
every etcd endpoint.

Disarm
the alarm.

### What does the etcd warning “etcdserver/api/v3rpc: transport: http2Server.HandleStreams failed to read frame: read tcp 127.0.0.1:2379->127.0.0.1:43020: read: connection reset by peer” mean?

This is gRPC-side warning when a server receives a TCP RST flag with client-side streams being prematurely closed. For example, a client closes its connection, while gRPC server has not yet processed all HTTP/2 frames in the TCP queue. Some data may have been lost in server side, but it is ok so long as client connection has already been closed.

Only
old versions of gRPC
log this. etcd
>=v3.2.13 by default log this with DEBUG level
, thus only visible with
--log-level=debug
flag enabled.

--log-level=debug

## Performance

### How should I benchmark etcd?

Try the
benchmark
tool. Current
benchmark results
are available for comparison.

### What does the etcd warning “apply entries took too long” mean?


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[FAQ](https://etcd.io/docs/v3.7/faq/)
