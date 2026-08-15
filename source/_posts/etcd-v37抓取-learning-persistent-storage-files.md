---
title: etcd v3.7 抓取：etcd persistent storage files
date: 2026-09-13 10:04:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/learning/persistent-storage-files/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/learning/persistent-storage-files/>

---

This document explains the etcd persistent storage format: naming, content and tools that allow developers to inspect them. Going forward the document should be extended with changes to the storage model. This document is targeted at etcd developers to help with their data recovery needs.

## Prerequisites

The following articles provide helpful background information for this document:

etcd data model overview:
https://etcd.io/docs/v3.6/learning/data_model

Raft overview:
https://raft.github.io/raft.pdf
(especially “5.3 Log replication” section).

## Overview

### Long leaving files

```
./member/snap/db
```

```
./member/snap/0000000000000002-0000000000049425.snap
./member/snap/0000000000000002-0000000000061ace.snap
```

Periodic
snapshots of legacy v2 store
, containing:
basic membership information
etcd-version

basic membership information

etcd-version

As of etcd v3, the content is redundant to the content of /snap/db files.

Periodically (
30s
) these files
are purged
, and the last
--max-snapshots=5
are preserved.

--max-snapshots=5

```
/member/snap/000000000007a178.snap.db
```

A complete
bbolt snapshot downloaded
from the etcd leader if the replica was lagging too much.

Has the same type of content as (
./member/snap/db
) file.

./member/snap/db

The file is used in 2 scenarios:
In response to the leader's request to recover from the snapshot.
During the server startup
, when the last snapshot (.snap.db file) is found and detected to be having a newer index than the consistent_index in the current
snap.db
file.
Note: Periodic snapshots generated on each replica are only emitted in the form of *.snap file (not snap.db file). So there is no guarantee the most recent snapshot (in WAL log) has the *.snap.db file. But in such a case the backend (snap/db) is expected to be newer than the snapshot.

In response to the leader's request to recover from the snapshot.

During the server startup
, when the last snapshot (.snap.db file) is found and detected to be having a newer index than the consistent_index in the current
snap.db
file.

snap.db

The file
is not being deleted when the recovery is over
(so whole content is populated to ./member/snap/db file). Periodically (
30s
) the files
are
purged.
Here also
--max-snapshots=5
are preserved. As these files can be O(GBs) this might create a risk of disk space exhaustion.

--max-snapshots=5

```
./member/wal/000000000000000f-00000000000b38c7.wal
./member/wal/000000000000000e-00000000000a7fe3.wal
./member/wal/000000000000000d-000000000009c70c.wal
```

Raft’s Write Ahead Logs
, containing recent transactions accepted by Raft, periodic snapshots or CRC records.

Recent
--max-wals=5
files are being preserved. Each of these files is
~64*10^6
bytes. The file is cut when it exceeds this hardcoded size, so the files might slightly exceed that size (so the preallocated
0.tmp
does not offer full disk-exceeded protection).

--max-wals=5

~64*10^6

0.tmp

If the snapshots are too infrequent, there can be more than
--max-wals=5
, as file-system level locks are protecting the files preventing them from being deleted too early.

--max-wals=5

```
./member/wal/0.tmp (or .../1.tmp)
```

### Temporary files

During etcd internal processing, it is possible that several short living files might be encountered:

```
./member/snap/0000000000000002-000000000007a178.snap.broken
```

Snapshot files are renamed as ‘broken’ when they cannot be
loaded
.
The attempt to load the newest file happens when etcd is being
started
.
Or during backup/migrate commands of etcdctl.

The attempt to load the newest file happens when etcd is being
started
.
Or during backup/migrate commands of etcdctl.

The attempt to load the newest file happens when etcd is being
started
.

Or during backup/migrate commands of etcdctl.

```
./member/snap/tmp071677638 (random suffix)
```

Temporary
(bbolt) file created on replicas in response to the msgSnap leaders request, so to the demand from the leader to recover storage from the given snapshot.

After successful (complete) retrieval of content the file is
renamed
to:
/member/snap/[SNAPSHOT-INDEX].snap.db
. In case of a server dying / being killed in the middle of the files download, the files remain on disk and are never automatically cleaned.They can be substantial in size (GBs).

/member/snap/[SNAPSHOT-INDEX].snap.db

See
etcd/issues/12837
.
Fixed in etcd 3.5.

```
/member/snap/db.tmp.071677638 (random suffix)
```

A temporary file that contains a copy of the backend content (/member/snap/db), during the
process of defragmentation
. After the successful process the file is renamed to /member/snap/db, replacing the original backend.

On etcd server startup these files get
pruned
.

## bbolt b+tree:
member/snap/db

This file contains the main etcd content, applied to a specific point of the Raft log (see
consistent_index
).

### Physical organization

The better bolt storage is physically organized as a
b+tree
. The physical pages of b-tree are never modified in-place
1
. Instead, the content is copied to a new page (reclaimed from the freepages list) and the old page is added to the free-pages list as soon as there is no open transaction that might access it. Thanks to this process, an open RO transaction sees a consistent historical state of the storage. The RW transaction is exclusive and blocking all other RW transactions.
Big values are stored on multiple continuous pages. The process of page reclamation combined with a need to allocate contiguous areas of pages of different sizes might lead to growing fragmentation of the bbolt storage.

The bbolt file never shrinks on its own. Only in the defragmentation process, the file can be rewritten to a new one that has some buffer of free pages on its end and has truncated size.

### Logical organization

The bbolt storage is divided into buckets. In each bucket there are stored keys (byte[]->value byte[] pairs), in lexicographical order. The list below represents buckets used by etcd (as of version 3.5) and the keys in use.

rpcpb.Alarm
:
{MemberID, Alarm: NONE|NOSPACE|CORRUPT}

nil

""

BigEndian.PutUint64

Any change of Roles or Users increments this field on transaction commit.

The value is used only for
optimistic locking during
the authorization process.

authpb.Role

authpb.User

"3.5.0"

```
{
  "target-version": "3.4.0"
  "enabled": true/false
}
```

Persists intent configured by the most recent:
Downgrade RPC
request.

Downgrade RPC

Since v3.5

[revisionId] encoded using
bytesToRev
{main,sub}

The key-value deletes are marshalled with 't' at the end (as a "Tombstone")

mvccpb.KeyValue

key, create_rev, mod_rev, version, value, lease id

leasepb.Lease

Note: LeaseCheckpoint is extending only RemainingTTL. Just TTL is from the original Grant.

Note2: We persist TTLs in seconds (from the undefined 'now'). Crash-looping server does not release leases!!!

"8e9e05c52164694d"

```
{
  "id":10276657743932975437,
  "peerURLs":[
  "
http://localhost:2380
"],
  "name":"default",
  "clientURLs": ["http://localhost:2379"]
}
```

"8e9e05c52164694d"

[]byte("removed")

Ids of all removed members. Used to validate that a removed member is never added again under the same id.

The field is currently (3.4) read from store V2 and never from V3
. See
https://github.com/etcd-io/etcd/pull/12820

### Tools

#### bbolt

bbolt has a command line tool that enables inspecting the file content.

Examples of use:

```
% go run go.etcd.io/bbolt/cmd/bbolt buckets ./default.etcd/member/snap/db
```

```
% go run go.etcd.io/bbolt/cmd/bbolt get ./default.etcd/member/snap/db cluster clusterVersion
```

#### etcd-dump-db

etcd-dump-db can be used to list content of v3 etcd backend (bbolt).

```
% go run go.etcd.io/etcd/v3/tools/etcd-dump-db  list-bucket default.etcd
alarm
auth
...
```

See more examples in:
https://github.com/etcd-io/etcd/tree/master/tools/etcd-dump-db

## WAL: Write ahead log

Write ahead log is a Raft persistent storage that is used to store proposals. First the leader stores the proposal in its log and then (concurrently) replicates it using Raft protocol to followers. Each follower persists the proposal in its WAL before confirming back replication to the leader.

The WAL log used in etcd differs from canonical Raft model 2-fold:

It does persist not only indexed entries, but also Raft snapshots (lightweight) & hard-state. So the entire Raft state of the member can be recovered from the WAL log alone.

It is append-only. Entries are not overridden in place, but an entry appended later in the file (with the same index) is superseding the previous one.

### File names

The WAL log files are named using following pattern:

```
"%016x-%016x.wal", seq, index
```

Example:
./member/wal/0000000000000010-00000000000bf1e6.wal

./member/wal/0000000000000010-00000000000bf1e6.wal

So the file names contains hex-encoded:

Sequential number of the WAL log file

Index of the first entry or snapshot in the file.
In particular the first file “0000000000000000-0000000000000000.wal” has the initial snapshot record with index=0.

### Physical content

The WAL log file contains a sequence of “
Frames
”. Each frame contains:

LittleEndian
2
encoded uint64 that contains the length of the marshalled
walpb.Record
(3).

Padding: Some number of 0 bytes, such that whole frame has aligned (mod 8) size

Marshalled
walpb.Record
data:
type
- int encoded enum driving interpretation of the data-field below
data - depending on type, usually marshalled proto
crc - RC-32 checksum of all “data” fields combined (no type) in all the log records on this particular replica since WAL log creation. Please note that CRC takes in consideration ALL records (even if they didn’t get committedcomitted by Raft).

type
- int encoded enum driving interpretation of the data-field below

data - depending on type, usually marshalled proto

crc - RC-32 checksum of all “data” fields combined (no type) in all the log records on this particular replica since WAL log creation. Please note that CRC takes in consideration ALL records (even if they didn’t get committedcomitted by Raft).

The files are “cut” (new file is started) when the current file is exceeding
64*10^6
bytes.

64*10^6

### Logical content

Write ahead log files in the logical layer contains:

Raftpb.Entry:
recent proposals replicated by Raft leader. Some of these proposals are considered ‘committed’ and the others are subject to be logically overridden.

Raftpb.Entry:

Raftpb.HardState(term,commit,vote):
periodic (very frequent) information about the index of a log entry that is ‘committed’ (replicated to the majority of servers), so guaranteed to be not changed/overridden and that can be applied to the backends (v2, v3). It also contains a “term” (indicator whether there were any election related changes) and a vote - a member the current replica voted for in the current term.

Raftpb.HardState(term,commit,vote):

walpb.Snapshot(term, index):
periodic snapshots of Raft state (no DB content, just snapshot log index and Raft term)
V2 store content is stored in a separate *.store files.
V3 store content is maintained in the bbolt file, and it’s becoming an implicit snapshot as soon as entries are applied there.

walpb.Snapshot(term, index):

V2 store content is stored in a separate *.store files.

V3 store content is maintained in the bbolt file, and it’s becoming an implicit snapshot as soon as entries are applied there.

crc32 checksum record (at the beginning of each file), used to resume CRC checking for the remainder of the file.

etcdserverpb.Metadata(node_id, cluster_id)
- identifying the cluster & replica the log represents.

etcdserverpb.Metadata(node_id, cluster_id)

Each WAL-log file is build from (in order):

CRC-32 frame (running crc from all previous files, 0 for the first file).

Metadata frame (cluster & replica IDs)


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[etcd persistent storage files](https://etcd.io/docs/v3.7/learning/persistent-storage-files/)
