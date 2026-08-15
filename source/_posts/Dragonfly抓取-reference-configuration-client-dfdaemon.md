---
title: Dragonfly 抓取：Dfdaemon
date: 2026-09-14 10:05:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/reference/configuration/client/dfdaemon/>

---

## Configure Dfdaemon YAML File

Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
.

```
# host is the host configuration for dfdaemon.
host
:
# idc is the idc of the host.
idc
:
''
# location is the location of the host.
location
:
''
# # hostname is the hostname of the host.
# hostname: ""
# # ip is the advertise ip of the host.
# ip: ""
#
# schedulerClusterID is the ID of the cluster to which the scheduler belongs.
# NOTE: This field is used to identify the cluster to which the scheduler belongs.
# If this flag is set, the idc, location, hostname and ip will be ignored when listing schedulers.
schedulerClusterID
:
1
server
:
# pluginDir is the directory to store plugins.
pluginDir
:
/var/lib/dragonfly/plugins/dfdaemon/
# cacheDir is the directory to store cache files.
cacheDir
:
/var/cache/dragonfly/dfdaemon/
# BBR-inspired adaptive rate limiter configuration for gRPC servers (download & upload).
# When system CPU or memory usage exceeds the configured thresholds, the limiter
# estimates capacity via `max_pass × min_rt × bucket_count / 1000` and sheds
# incoming requests whose in-flight count exceeds this estimate. A cooldown
# period prevents rapid oscillation between shedding and accepting.
adaptiveRateLimit
:
# Number of time buckets in the rolling window for metric aggregation.
bucketCount
:
50
# Duration of each time bucket (e.g., 200ms).
bucketInterval
:
200ms
# CPU usage percentage threshold (0–100) above which the system is
# considered overloaded. If threshold is 100, CPU usage is ignored
# for overload detection.
cpuThreshold
:
100
# Memory usage percentage threshold (0–100) above which the system is
# considered overloaded. If threshold is 100, Memory usage is ignored
# for overload detection.
memoryThreshold
:
90
# Duration to continue shedding incoming requests after the first drop
# event, preventing rapid oscillation between shedding and accepting.
shedCooldown
:
5s
# How often the background task collects CPU/memory usage metrics.
collectInterval
:
3s
download
:
# protocol that peers use to download piece, supported values: "tcp", "quic".
# When dfdaemon acts as a parent, it announces this protocol so downstream
# peers fetch pieces using it.
#
# QUIC: Recommended for high-bandwidth, long-RTT, or lossy networks.
# TCP: Recommended for high-bandwidth, low-RTT, or local-area network (LAN) environments.
protocol
:
tcp
server
:
# socketPath is the unix socket path for dfdaemon GRPC service.
socketPath
:
/var/run/dragonfly/dfdaemon.sock
# The rate limit for the requests on the download gRPC server.
#
# This limit applies to the total number of gRPC requests per second, including:
# - Multiple requests within a single connection.
# - Single requests across different connections.
requestRateLimit
:
400
# The buffer size for the request channel on the download gRPC server.
#
# This controls the capacity of the bounded channel used to queue
# incoming gRPC requests before they are processed. If the buffer is full,
# new requests will return a `RESOURCE_EXHAUSTED` error.
requestBufferSize
:
50
# bandwidthLimit is the default rate limit of the download speed in KB/MB/GB per second, default is 50GB/s.
bandwidthLimit
:
50GB
# backToSourceBandwidthLimit is the rate limit of the back to source speed in KB/MB/GB per second, default is 50GB/s.
backToSourceBandwidthLimit
:
50GB
# pieceTimeout is the timeout for downloading a piece from source.
pieceTimeout
:
360s
# collectedPieceTimeout is the timeout for collecting one piece from the parent in the stream.
collectedPieceTimeout
:
360s
# concurrentPieceCount is the number of concurrent pieces to download.
concurrentPieceCount
:
32
upload
:
server
:
# port is the port to the grpc server.
port
:
4000
# # ip is the listen ip of the grpc server.
# ip: ""
# # CA certificate file path for mTLS.
# caCert: /etc/ssl/certs/ca.crt
# # GRPC server certificate file path for mTLS.
# cert: /etc/ssl/certs/server.crt
# # GRPC server key file path for mTLS.
# key: /etc/ssl/private/server.pem
#
# The rate limit for the requests on the upload gRPC server.
#
# This limit applies to the total number of gRPC requests per second, including:
# - Multiple requests within a single connection.
# - Single requests across different connections.
requestRateLimit
:
400
# The buffer size for the request channel on the upload gRPC server.
#
# This controls the capacity of the bounded channel used to queue
# incoming gRPC requests before they are processed. If the buffer is full,
# new requests will return a `RESOURCE_EXHAUSTED` error.
requestBufferSize
:
50
# # Client configuration for remote peer's upload server.
# client:
#   # CA certificate file path for mTLS.
#   caCert: /etc/ssl/certs/ca.crt
#   # GRPC client certificate file path for mTLS.
#   cert: /etc/ssl/certs/client.crt
#   # GRPC client key file path for mTLS.
#   key: /etc/ssl/private/client.pem
# disableShared indicates whether disable to share data for other peers.
disableShared
:
false
# bandwidthLimit is the default rate limit of the upload speed in KB/MB/GB per second, default is 50GB/s.
bandwidthLimit
:
50GB
# manager:
# # addr is manager address. The addr is optional. If the addr is not configured,
# # dfdaemon runs without the manager, and the dynamic configuration is loaded
# # from the local dynconfig.yaml file instead of being fetched from the manager,
# # refer to Configure Dfdaemon Dynconfig YAML File.
# addr: http://manager-service:65003
# # CA certificate file path for mTLS.
# caCert: /etc/ssl/certs/ca.crt
# # GRPC client certificate file path for mTLS.
# cert: /etc/ssl/certs/client.crt
# # GRPC client key file path for mTLS.
# key: /etc/ssl/private/client.pem
scheduler
:
# announceInterval is the interval to announce peer to the scheduler.
# Announcer will provide the scheduler with peer information for scheduling,
# peer information includes cpu, memory, etc.
announceInterval
:
1m
# scheduleTimeout is timeout for the scheduler to respond to a scheduling request from dfdaemon, default is 3 hours.
#
# If the scheduler's response time for a scheduling decision exceeds this timeout,
# dfdaemon will encounter a `TokioStreamElapsed(Elapsed(()))` error.
#
# Behavior upon timeout:
#   - If `enable_back_to_source` is `true`, dfdaemon will attempt to download directly
#     from the source.
#   - Otherwise (if `enable_back_to_source` is `false`), dfdaemon will report a download failure.
#
# **Important Considerations Regarding Timeout Triggers**:
# This timeout isn't solely for the scheduler's direct response. It can also be triggered
# if the overall duration of the client's interaction with the scheduler for a task
# (e.g., client downloading initial pieces and reporting their status back to the scheduler)
# exceeds `schedule_timeout`. During such client-side processing and reporting,
# the scheduler might be awaiting these updates before sending its comprehensive
# scheduling response, and this entire period is subject to the `schedule_timeout`.
#
# **Configuration Guidance**:
# To prevent premature timeouts, `schedule_timeout` should be configured to a value
# greater than the maximum expected time for the *entire scheduling interaction*.
# This includes:
#   1. The scheduler's own processing and response time.
#   2. The time taken by the client to download any initial pieces and download all pieces finished,
#      as this communication is part of the scheduling phase.
#
# Setting this value too low can lead to `TokioStreamElapsed` errors even if the
# network and scheduler are functioning correctly but the combined interaction time
# is longer than the configured timeout.
scheduleTimeout
:
3h
# maxScheduleCount is the max count of schedule.
maxScheduleCount
:
5
# enableBackToSource indicates whether enable back-to-source download, when the scheduling failed.
enableBackToSource
:
true
# # CA certificate file path for mTLS.
# caCert: /etc/ssl/certs/ca.crt
# # GRPC client certificate file path for mTLS.
# cert: /etc/ssl/certs/client.crt
# # GRPC client key file path for mTLS.
# key: /etc/ssl/private/client.pem
seedPeer
:
server
:
# port is the 
```

## Configure Dfdaemon Dynconfig YAML File

When
manager.addr
is not configured, dfdaemon runs without the manager and loads the
dynamic configuration from a local
dynconfig.yaml
file (typically mounted as a
Kubernetes ConfigMap) instead of fetching it from the manager.

Configure
dynconfig.yaml
, the default path is
/etc/dragonfly/dynconfig.yaml
. The path can
be overridden with the
--dynconfig
flag or the
DFDAEMON_DYNCONFIG
environment variable.
If the file does not exist, it is generated with the default values on startup. The
configuration is refreshed periodically according to the
dynconfig.refreshInterval
in
dfdaemon.yaml
, default is
1m
.

Scheduler discovery supports two modes: if the static address list
scheduler.addrs
is
non-empty, it takes precedence; otherwise dfdaemon resolves the scheduler headless service
address
scheduler.addr
via DNS to obtain the list of scheduler addresses. Each discovered
scheduler is health-checked, and unhealthy schedulers are filtered out.

```
scheduler
:
# addr is the address of the scheduler headless service with port, resolved via DNS
# to discover all scheduler addresses.
addr
:
'scheduler-headless.default.svc:8002'
# # addrs is the static list of scheduler addresses with port.
# # When non-empty, it takes precedence over addr.
# addrs: ['192.168.1.10:8002', '192.168.1.11:8002']
# clientConfig is the block list configuration for clients running as normal peers.
clientConfig
:
blockList
:
task
:
download
:
# applications is the blocked application names.
applications
:
[
]
# urls is the blocked URL regex patterns.
urls
:
[
]
# tags is the blocked tags.
tags
:
[
]
# priorities is the blocked priorities.
priorities
:
[
]
persistentTask
:
upload
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
download
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
priorities
:
[
]
persistentCacheTask
:
upload
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
download
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
priorities
:
[
]
# seedClientConfig is the block list configuration for clients running as seed peers,
# the structure is the same as clientConfig.
seedClientConfig
:
blockList
:
task
:
download
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
priorities
:
[
]
persistentTask
:
upload
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
download
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
priorities
:
[
]
persistentCacheTask
:
upload
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
download
:
applications
:
[
]
urls
:
[
]
tags
:
[
]
priorities
:
[
]
```

---

> 完整与最新内容以官方文档为准：[Dfdaemon](https://d7y.io/docs/next/reference/configuration/client/dfdaemon/)
