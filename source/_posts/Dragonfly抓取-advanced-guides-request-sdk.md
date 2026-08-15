---
title: Dragonfly 抓取：Request SDK
date: 2026-09-14 09:41:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/request-sdk/>

---

## Background

A SDK for routing User requests to Seed Peers using consistent hashing, replacing the previous Kubernetes Service load balancing approach.

For example, when Nydus downloads layer chunks via HTTP Range requests through Kubernetes Service load balancing:

Same layer may be downloaded multiple times (once per Seed Peer).

Low cache hit rate due to requests being distributed across different Seed Peers.

Prefetch functionality cannot be effectively utilized.

### Goals

Reduce redundant origin downloads.

Improve chunk cache hit rate.

Provide SDK integration with clear error handling.

## Architecture

### Task ID-Based Routing

Generate Task ID using
dragonfly_client_util::id_generator::IDGenerator
.

Route all chunks of the same layer to the same Seed Peer via consistent hashing.

### Consistent Hash Implementation

Element format
:
IP:Port
.

Key format
:
Task ID
.

Uses virtual nodes for load distribution.

Seed Peers run as StatefulSet ensuring stable IP/Port.

## Usage

Add the dependency to your
Cargo.toml
:

```
[dependencies]
dragonfly-client-util = "1"
```

The SDK provides a Request trait that enables efficient communication with Dragonfly Seed Peers through consistent hashing.
This approach ensures that all chunks of the same layer are routed to the same Seed Peer, significantly improving cache
hit rates and reducing redundant origin downloads.

```
/// Defines the interface for sending requests via the Dragonfly.
///
/// This trait enables interaction with remote servers through the Dragonfly, providing methods
/// for performing GET requests with flexible response handling. It is designed for clients that
/// need to communicate with Dragonfly seed client efficiently, supporting both streaming and buffered
/// response processing. The trait shields the complex request logic between the client and the
/// Dragonfly seed client's proxy, abstracting the underlying communication details to simplify
/// client implementation and usage.
#[tonic::async_trait]
pub
trait
Request
{
/// Sends an GET request to a remote server via the Dragonfly and returns a response
/// with a streaming body.
///
/// This method is designed for scenarios where the response body is expected to be processed as a
/// stream, allowing efficient handling of large or continuous data. The response includes metadata
/// such as status codes and headers, along with a streaming `Body` for accessing the response content.
async
fn
get
(
&
self
,
request
:
GetRequest
)
->
Result
<
GetResponse
<
Body
>>
;
/// Sends an GET request to a remote server via the Dragonfly and writes the response
/// body directly into the provided buffer.
///
/// This method is optimized for scenarios where the response body needs to be stored directly in
/// memory, avoiding the overhead of streaming for smaller or fixed-size responses. The provided
/// `BytesMut` buffer is used to store the response content, and the response metadata (e.g., status
/// and headers) is returned separately.
async
fn
get_into
(
&
self
,
request
:
GetRequest
,
buf
:
&
mut
BytesMut
)
->
Result
<
GetResponse
>
;
}
```

For more details, please refer to
dragonfly-client-util
.

---

> 完整与最新内容以官方文档为准：[Request SDK](https://d7y.io/docs/next/advanced-guides/request-sdk/)
