---
title: etcd v3.7 抓取：etcd API
date: 2026-09-13 10:03:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/learning/api/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/learning/api/>

---

This document is meant to give an overview of the v3 etcd APIs central design.
This should not be mistaken with etcd v2 API, deprecated in etcd v3.5.
It is by no means all encompassing, but intended to focus on the basic ideas needed to understand etcd without the distraction of less common API calls.
All etcd APIs are defined in
gRPC services
, which categorize remote procedure calls (RPCs) understood by the etcd server.
A full listing of all etcd RPCs are documented in markdown in the
gRPC API listing
.

## gRPC Services

Every API request sent to an etcd server is a gRPC remote procedure call. RPCs in etcd are categorized based on functionality into services.

Services important for dealing with etcd’s key space include:

KV - Creates, updates, fetches, and deletes key-value pairs.

Watch - Monitors changes to keys.

Lease - Primitives for consuming client keep-alive messages.

Services which manage the cluster itself include:

Auth - Role based authentication mechanism for authenticating users.

Cluster - Provides membership information and configuration facilities.

Maintenance - Takes recovery snapshots, defragments the store, and returns per-member status information.

### Requests and Responses

All RPCs in etcd follow the same format. Each RPC has a function
Name
which takes
NameRequest
as an argument and returns
NameResponse
as a response. For example, here is the
Range
RPC description:

Name

NameRequest

NameResponse

Range

```
service
KV
{
Range
(
RangeRequest
)
returns
(
RangeResponse
)
...
}
```

### Response header

All Responses from etcd API have an attached response header which includes cluster metadata for the response:

```
message
ResponseHeader
{
uint64
cluster_id
=
1
;
uint64
member_id
=
2
;
int64
revision
=
3
;
uint64
raft_term
=
4
;
}
```

Cluster_ID - the ID of the cluster generating the response.

Member_ID - the ID of the member generating the response.

Revision - the revision of the key-value store when generating the response.

Raft_Term - the Raft term of the member when generating the response.

An application may read the
Cluster_ID
or
Member_ID
field to ensure it is communicating with the intended cluster (member).

Cluster_ID

Member_ID

Applications can use the
Revision
field to know the latest revision of the key-value store. This is especially useful when applications specify a historical revision to make a
time travel query
and wish to know the latest revision at the time of the request.

Revision

time travel query

Applications can use
Raft_Term
to detect when the cluster completes a new leader election.

Raft_Term

## Key-Value API

The Key-Value API manipulates key-value pairs stored inside etcd. The majority of requests made to etcd are usually key-value requests.

### System primitives

### Key-Value pair

A key-value pair is the smallest unit that the key-value API can manipulate. Each key-value pair has a number of fields, defined in
protobuf format
:

```
message
KeyValue
{
bytes
key
=
1
;
int64
create_revision
=
2
;
int64
mod_revision
=
3
;
int64
version
=
4
;
bytes
value
=
5
;
int64
lease
=
6
;
}
```

Key - key in bytes. An empty key is not allowed.

Value - value in bytes.

Version - version is the version of the key. A deletion resets the version to zero and any modification of the key increases its version.

Create_Revision - revision of the last creation on the key.

Mod_Revision - revision of the last modification on the key.

Lease - the ID of the lease attached to the key. If lease is 0, then no lease is attached to the key.

In addition to just the key and value, etcd attaches additional revision metadata as part of the key message. This revision information orders keys by time of creation and modification, which is useful for managing concurrency for distributed synchronization. The etcd client’s
distributed shared locks
use the creation revision to wait for lock ownership. Similarly, the modification revision is used for detecting
software transactional memory
read set conflicts and waiting on
leader election
updates.

#### Revisions

etcd maintains a 64-bit cluster-wide counter, the store revision, that is incremented each time the key space is modified. The revision serves as a global logical clock, sequentially ordering all updates to the store. The change represented by a new revision is incremental; the data associated with a revision is the data that changed the store. Internally, a new revision means writing the changes to the backend’s B+tree, keyed by the incremented revision.

Revisions become more valuable when considering etcd’s
multi-version concurrency control
backend. The MVCC model means that the key-value store can be viewed from past revisions since historical key revisions are retained. The retention policy for this history can be configured by cluster administrators for fine-grained storage management; usually etcd discards old revisions of keys on a timer. A typical etcd cluster retains superseded key data for hours. This also provides reliable handling for long client disconnection, not just transient network disruptions: watchers simply resume from the last observed historical revision. Similarly, to read from the store at a particular point-in-time, read requests can be tagged with a revision to return keys from a view of the key space at the point-in-time that revision was committed.

#### Key ranges

The etcd data model indexes all keys over a flat binary key space. This differs from other key-value store systems that use a hierarchical system of organizing keys into directories. Instead of listing keys by directory, keys are listed by key intervals
[a, b)
.

[a, b)

These intervals are often referred to as “ranges” in etcd. Operations over ranges are more powerful than operations on directories. Like a hierarchical store, intervals support single key lookups via
[a, a+1)
(e.g., [‘a’, ‘a\x00’) looks up ‘a’) and directory lookups by encoding keys by directory depth. In addition to those operations, intervals can also encode prefixes; for example the interval
['a', 'b')
looks up all keys prefixed by the string ‘a’.

[a, a+1)

['a', 'b')

By convention, ranges for a request are denoted by the fields
key
and
range_end
. The
key
field is the first key of the range and should be non-empty. The
range_end
is the key following the last key of the range. If
range_end
is not given or empty, the range is defined to contain only the key argument. If
range_end
is
key
plus one (e.g., “aa”+1 == “ab”, “a\xff”+1 == “b”), then the range represents all keys prefixed with key. If both
key
and
range_end
are ‘\0’, then range represents all keys. If
range_end
is ‘\0’, the range is all keys greater than or equal to the key argument.

key

range_end

key

range_end

key

range_end

### Range

Keys are fetched from the key-value store using the
Range
API call, which takes a
RangeRequest
:

Range

RangeRequest

```
message
RangeRequest
{
enum
SortOrder
{
NONE
=
0
;
// default, no sorting
ASCEND
=
1
;
// lowest target value first
DESCEND
=
2
;
// highest target value first
}
enum
SortTarget
{
KEY
=
0
;
VERSION
=
1
;
CREATE
=
2
;
MOD
=
3
;
VALUE
=
4
;
}
bytes
key
=
1
;
bytes
range_end
=
2
;
int64
limit
=
3
;
int64
revision
=
4
;
SortOrder
sort_order
=
5
;
SortTarget
sort_target
=
6
;
bool
serializable
=
7
;
bool
keys_only
=
8
;
bool
count_only
=
9
;
int64
min_mod_revision
=
10
;
int64
max_mod_revision
=
11
;
int64
min_create_revision
=
12
;
int64
max_create_revision
=
13
;
}
```

Key, Range_End - The key range to fetch.

Limit - the maximum number of keys returned for the request. When limit is set to 0, it is treated as no limit.

Revision - the point-in-time of the key-value store to use for the range. If revision is less or equal to zero, the range is over the latest key-value store. If the revision is compacted, ErrCompacted is returned as a response.

Sort_Order - the ordering for sorted requests.

Sort_Target - the key-value field to sort.

Serializable - sets the range request to use serializable member-local reads. By default, Range is linearizable; it reflects the current consensus of the cluster. For better performance and availability, in exchange for possible stale reads, a serializable range request is served locally without needing to reach consensus with other nodes in the cluster.

Keys_Only - return only the keys and not the values.

Count_Only - return only the count of the keys in the range.

Min_Mod_Revision - the lower bound for key mod revisions; filters out lesser mod revisions.

Max_Mod_Revision - the upper bound for key mod revisions; filters out greater mod revisions.

Min_Create_Revision - the lower bound for key create revisions; filters out lesser create revisions.

Max_Create_Revision - the upper bound for key create revisions; filters out greater create revisions.

The client receives a
RangeResponse
message from the
Range
call:

RangeResponse

Range

```
message
RangeResponse
{
ResponseHeader
header
=
1
;
repeated
mvccpb.KeyValue
kvs
=
2
;
bool
more
=
3
;
int64
count
=
4
;
}
```

Kvs - the list of key-value pairs matched by the range request. When
Count_Only
is set,
Kvs
is empty.

Count_Only

Kvs

More - indicates if there are more keys to return in the requested range if
limit
is set.

limit

Count - the total number of keys satisfying the range request.

For large key ranges where buffering the full response is undesirable, see
RangeStream
.

### RangeStream

RangeStream
returns the same result set as
Range
, but the server splits the response into a sequence of chunks and streams them to the client. This avoids buffering large ranges entirely in memory on either side.
RangeStream
accepts the same
RangeRequest
as
Range
.

RangeStream

Range

RangeStream

RangeRequest

Range

The client receives a stream of
RangeStreamResponse
messages from the
RangeStream
call:

RangeStreamResponse

RangeStream

```
message
RangeStreamResponse
{
RangeResponse
range_response
=
1
;
}
```

Field population across chunks:

Kvs - each chunk carries a disjoint slice of the result. Concatenating the
kvs
from every chunk in the order they arrive yields the same key set as a single
Range
call.

kvs

Range

Header, More, Count - populated only on the final chunk, and only when the stream completes without error. Earlier chunks leave these fields zero-valued. Applying
proto.Merge
over every chunk’s
range_response
yields a
RangeResponse
equivalent to what
Range
would have returned.

proto.Merge

range_response

RangeResponse

Range

If the stream ends in error, no chunk carries a valid
header
,
more
, or
count
.

header

more

count

Every chunk in the stream is served against the same revision. If the request does not set
Revision
, the server captures the latest committed revision when the stream starts and reuses it for the rest of the stream.

Revision

RangeStream
does not support custom sort orders or revision filters (
min_mod_revision
,
max_mod_revision
,
min_create_revision
,
max_create_revision
). Requests that use either return
Unimplemented
.
RangeStream
is also not supported by the etcd gRPC proxy.

RangeStream

min_mod_revision

max_mod_revision

min_create_revision

max_create_revision

Unimplemented

RangeStream

There are two common ways to consume a
RangeStream
:

RangeStream

Process each chunk independently.
Suitable for high-performance scenarios where the client wants to decode and act on keys as they arrive rather than collecting the whole result first. The client iterates chunks and handles
kvs
from each one, then reads
header
,
more
, or
count
from the last chunk after the stream ends cleanly.

kvs

header

more

count


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[etcd API](https://etcd.io/docs/v3.7/learning/api/)
