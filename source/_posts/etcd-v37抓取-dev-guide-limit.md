---
title: etcd v3.7 抓取：System limits
date: 2026-09-13 09:54:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/dev-guide/limit/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/dev-guide/limit/>

---

## Request size limit

etcd is designed to handle small key value pairs typical for metadata. Larger requests will work, but may increase the latency of other requests. By default, the maximum size of any request is 1.5 MiB. This limit is configurable through
--max-request-bytes
flag for etcd server.

--max-request-bytes

## Storage size limit

The default storage size limit is 2 GiB, configurable with
--quota-backend-bytes
flag. 8 GiB is a suggested maximum size for normal environments and etcd warns at startup if the configured value exceeds it.

--quota-backend-bytes

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[System limits](https://etcd.io/docs/v3.7/dev-guide/limit/)
