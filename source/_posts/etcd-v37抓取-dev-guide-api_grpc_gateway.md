---
title: etcd v3.7 抓取：Why gRPC gateway
date: 2026-09-13 09:51:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/dev-guide/api_grpc_gateway/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/dev-guide/api_grpc_gateway/>

---

etcd v3 uses
gRPC
for its messaging protocol. The etcd project includes a gRPC-based
Go client
and a command line utility,
etcdctl
, for communicating with an etcd cluster through gRPC. For languages with no gRPC support, etcd provides a JSON
gRPC gateway
. This gateway serves a RESTful proxy that translates HTTP/JSON requests into gRPC messages.

## Using gRPC gateway

The gateway accepts a
JSON mapping
for etcd’s
protocol buffer
message definitions. Note that
key
and
value
fields are defined as byte arrays and therefore must be base64 encoded in JSON. The following examples use
curl
, but any HTTP/JSON client should work all the same.

key

value

curl

### Notes

gRPC gateway endpoint has changed since etcd v3.3:

etcd v3.2 or before uses only
[CLIENT-URL]/v3alpha/*
.

[CLIENT-URL]/v3alpha/*

etcd v3.3 uses
[CLIENT-URL]/v3beta/*
while keeping
[CLIENT-URL]/v3alpha/*
.

[CLIENT-URL]/v3beta/*

[CLIENT-URL]/v3alpha/*

etcd v3.4 uses
[CLIENT-URL]/v3/*
while keeping
[CLIENT-URL]/v3beta/*
.
[CLIENT-URL]/v3alpha/*
is deprecated
.

[CLIENT-URL]/v3/*

[CLIENT-URL]/v3beta/*

[CLIENT-URL]/v3alpha/*
is deprecated
.

[CLIENT-URL]/v3alpha/*

etcd v3.5 or later uses only
[CLIENT-URL]/v3/*
.
[CLIENT-URL]/v3beta/*
is deprecated
.

[CLIENT-URL]/v3/*

[CLIENT-URL]/v3beta/*
is deprecated
.

[CLIENT-URL]/v3beta/*

gRPC-gateway does not support authentication using TLS Common Name.

### Put and get keys

Use the
/v3/kv/range
and
/v3/kv/put
services to read and write keys:

/v3/kv/range

/v3/kv/put

```
<<COMMENT
https://www.base64encode.org/
foo is 'Zm9v' in Base64
bar is 'YmFy'
COMMENT
curl -L http://localhost:2379/v3/kv/put
\
-X POST -d
'{"key": "Zm9v", "value": "YmFy"}'
# {"header":{"cluster_id":"12585971608760269493","member_id":"13847567121247652255","revision":"2","raft_term":"3"}}
curl -L http://localhost:2379/v3/kv/range
\
-X POST -d
'{"key": "Zm9v"}'
# {"header":{"cluster_id":"12585971608760269493","member_id":"13847567121247652255","revision":"2","raft_term":"3"},"kvs":[{"key":"Zm9v","create_revision":"2","mod_revision":"2","version":"1","value":"YmFy"}],"count":"1"}
# get all keys prefixed with "foo"
curl -L http://localhost:2379/v3/kv/range
\
-X POST -d
'{"key": "Zm9v", "range_end": "Zm9w"}'
# {"header":{"cluster_id":"12585971608760269493","member_id":"13847567121247652255","revision":"2","raft_term":"3"},"kvs":[{"key":"Zm9v","create_revision":"2","mod_revision":"2","version":"1","value":"YmFy"}],"count":"1"}
```

### Watch keys

Use the
/v3/watch
service to watch keys:

/v3/watch

```
curl -N http://localhost:2379/v3/watch
\
-X POST -d
'{"create_request": {"key":"Zm9v"} }'
&
# {"result":{"header":{"cluster_id":"12585971608760269493","member_id":"13847567121247652255","revision":"1","raft_term":"2"},"created":true}}
curl -L http://localhost:2379/v3/kv/put
\
-X POST -d
'{"key": "Zm9v", "value": "YmFy"}'
>/dev/null 2>
&
1
# {"result":{"header":{"cluster_id":"12585971608760269493","member_id":"13847567121247652255","revision":"2","raft_term":"2"},"events":[{"kv":{"key":"Zm9v","create_revision":"2","mod_revision":"2","version":"1","value":"YmFy"}}]}}
```

### Transactions

Issue a transaction with
/v3/kv/txn
:

/v3/kv/txn

```
# target CREATE
curl -L http://localhost:2379/v3/kv/txn
\
-X POST
\
-d
'{"compare":[{"target":"CREATE","key":"Zm9v","createRevision":"2"}],"success":[{"requestPut":{"key":"Zm9v","value":"YmFy"}}]}'
# {"header":{"cluster_id":"12585971608760269493","member_id":"13847567121247652255","revision":"3","raft_term":"2"},"succeeded":true,"responses":[{"response_put":{"header":{"revision":"3"}}}]}
```

```
# target VERSION
curl -L http://localhost:2379/v3/kv/txn
\
-X POST
\
-d
'{"compare":[{"version":"4","result":"EQUAL","target":"VERSION","key":"Zm9v"}],"success":[{"requestRange":{"key":"Zm9v"}}]}'
# {"header":{"cluster_id":"14841639068965178418","member_id":"10276657743932975437","revision":"6","raft_term":"3"},"succeeded":true,"responses":[{"response_range":{"header":{"revision":"6"},"kvs":[{"key":"Zm9v","create_revision":"2","mod_revision":"6","version":"4","value":"YmF6"}],"count":"1"}}]}
```

### Authentication

Set up authentication with the
/v3/auth
service:

/v3/auth

```
# create root user
curl -L http://localhost:2379/v3/auth/user/add
\
-X POST -d
'{"name": "root", "password": "pass"}'
# {"header":{"cluster_id":"14841639068965178418","member_id":"10276657743932975437","revision":"1","raft_term":"2"}}
# create root role
curl -L http://localhost:2379/v3/auth/role/add
\
-X POST -d
'{"name": "root"}'
# {"header":{"cluster_id":"14841639068965178418","member_id":"10276657743932975437","revision":"1","raft_term":"2"}}
# grant root role
curl -L http://localhost:2379/v3/auth/user/grant
\
-X POST -d
'{"user": "root", "role": "root"}'
# {"header":{"cluster_id":"14841639068965178418","member_id":"10276657743932975437","revision":"1","raft_term":"2"}}
# enable auth
curl -L http://localhost:2379/v3/auth/enable -X POST -d
'{}'
# {"header":{"cluster_id":"14841639068965178418","member_id":"10276657743932975437","revision":"1","raft_term":"2"}}
```

Authenticate with etcd for an authentication token using
/v3/auth/authenticate
:

/v3/auth/authenticate

```
# get the auth token for the root user
curl -L http://localhost:2379/v3/auth/authenticate
\
-X POST -d
'{"name": "root", "password": "pass"}'
# {"header":{"cluster_id":"14841639068965178418","member_id":"10276657743932975437","revision":"1","raft_term":"2"},"token":"sssvIpwfnLAcWAQH.9"}
```

Set the
Authorization
header to the authentication token to fetch a key using authentication credentials:

Authorization

```
curl -L http://localhost:2379/v3/kv/put
\
-H
'Authorization: sssvIpwfnLAcWAQH.9'
\
-X POST -d
'{"key": "Zm9v", "value": "YmFy"}'
# {"header":{"cluster_id":"14841639068965178418","member_id":"10276657743932975437","revision":"2","raft_term":"2"}}
```

### Error responses

The gRPC gateway translates gRPC status into HTTP status codes and a JSON error
body. Starting in etcd v3.6, the upgrade to grpc-gateway v2 changed error
handling (see the v2 migration guide’s
error-handling note
),
and the gateway behavior now aligns with
google.rpc.Status
(code, message,
details) as described in
Google’s API error model
.
Historically, older grpc-gateway versions also included a top-level
error
field, but this field is not supported in etcd v3.6 and higher versions.

google.rpc.Status

error

Clients should treat the HTTP status code as the primary indicator of success or
failure. If a request fails, clients should rely on the
message
field as the
primary source of error information and use any additional details for further
context.

message

## Swagger

Generated
Swagger
API definitions can be found at
rpc.swagger.json
.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Why gRPC gateway](https://etcd.io/docs/v3.7/dev-guide/api_grpc_gateway/)
