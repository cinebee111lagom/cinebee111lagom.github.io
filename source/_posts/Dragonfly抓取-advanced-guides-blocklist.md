---
title: Dragonfly 抓取：Blocklist
date: 2026-09-14 09:37:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/blocklist/>

---

This document describes how to configure the blocklist for Dragonfly to disable specific
downloads, serving as an emergency measure to mitigate the impact of sudden abnormal requests
on the service. When a blocked download is intercepted, gRPC downloads will return a
PermissionDenied
error code, and HTTP proxy downloads will return a
FORBIDDEN
status.

## Configure blocklist in the manager console

In the deployment with Manager, the blocklist can be configured in the manager console.
The following diagram illustrates the blocklist configuration interface in the manager console.

## Configure blocklist without Manager

In the lightweight deployment (without the Manager), the blocklist can be configured in the
local
dynconfig.yaml
file of the client (typically mounted as a Kubernetes ConfigMap).
clientConfig.blockList
applies to clients running as normal peers, and
seedClientConfig.blockList
applies to clients running as seed peers. The configuration is
refreshed within one refresh interval, refer to
Configure Dfdaemon Dynconfig YAML File
.

Example
dynconfig.yaml
to block the downloads by application, URL regex, tag or priority:

```
scheduler
:
addr
:
'scheduler-headless.default.svc:8002'
clientConfig
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
'abnormal-app'
]
urls
:
[
'https://example.com/.*'
]
tags
:
[
'abnormal-tag'
]
priorities
:
[
]
```

For the helm charts, the blocklist can be configured with the
client.dynconfig
and
seedClient.dynconfig
values, which are rendered into the
dynconfig.yaml
ConfigMap.

---

> 完整与最新内容以官方文档为准：[Blocklist](https://d7y.io/docs/next/advanced-guides/blocklist/)
