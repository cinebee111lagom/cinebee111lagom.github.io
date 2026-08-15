---
title: etcd v3.7 抓取：Logging conventions
date: 2026-09-13 10:36:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/dev-internal/logging/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/dev-internal/logging/>

---

etcd uses the
zap
library for logging application output categorized into
levels
. A log message’s level is determined according to these conventions:

DebugLevel logs are typically voluminous, and are usually disabled in production.
Examples:
Send a normal message to a remote peer
Write a log entry to disk

DebugLevel logs are typically voluminous, and are usually disabled in production.

Examples:
Send a normal message to a remote peer
Write a log entry to disk

Send a normal message to a remote peer

Write a log entry to disk

InfoLevel is the default logging priority.
Examples:
Startup configuration
Start to do snapshot
Add a new node into the cluster
Add a new user into auth subsystem

InfoLevel is the default logging priority.

Examples:
Startup configuration
Start to do snapshot
Add a new node into the cluster
Add a new user into auth subsystem

Startup configuration

Start to do snapshot

Add a new node into the cluster

Add a new user into auth subsystem

WarnLevel logs are more important than Info, but don’t need individual human review.
Examples:
Failure to send Raft message to a remote peer
Failure to receive heartbeat message within the configured election timeout

WarnLevel logs are more important than Info, but don’t need individual human review.

Examples:
Failure to send Raft message to a remote peer
Failure to receive heartbeat message within the configured election timeout

Failure to send Raft message to a remote peer

Failure to receive heartbeat message within the configured election timeout

ErrorLevel logs are high-priority. If an application is running smoothly, it shouldn’t generate any error-level logs.
Examples:
Failure to allocate disk space for WAL

ErrorLevel logs are high-priority. If an application is running smoothly, it shouldn’t generate any error-level logs.

Examples:
Failure to allocate disk space for WAL

Failure to allocate disk space for WAL

PanicLevel logs a message, then panics.
Examples:
Failure to encode Raft messages

PanicLevel logs a message, then panics.

Examples:
Failure to encode Raft messages

Failure to encode Raft messages

FatalLevel logs a message, then calls os.Exit(1).
Examples:
Failure to save Raft snapshot

FatalLevel logs a message, then calls os.Exit(1).

Examples:
Failure to save Raft snapshot

Failure to save Raft snapshot

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Logging conventions](https://etcd.io/docs/v3.7/dev-internal/logging/)
