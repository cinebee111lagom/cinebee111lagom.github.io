---
title: Dragonfly 抓取：v2.3
date: 2026-09-14 10:14:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/roadmap-v2.3/>

---

Manager:

Configure scheduling weights.

Support scopes for Personal Access Tokens (PATs).

Display more Peer information in the console, such as CPU and memory usage.

Display persistent cache information of peers in the console.

Add management of sync peers in the console.

Add audit logging for security-sensitive actions(RBAC, PATs, etc.).

Scheduler:

Optimize the scheduling algorithm to improve bandwidth utilization in the P2P network.

Client:

Download file content via UDS(Unix domain socket) transmission,
dfget
calls UDS for downloading and output
the file content to the path specified by the option
--output
.

Define a codable protocol for data transmission, providing faster encoding/decoding.

Support persistent cache, allowing access within the P2P cluster without uploading to other storage,
facilitating faster read/write of AI models and datasets.

Allow peers to get the QoS of parents and select the optimal parents for downloading.

Preheat files in the memory cache to improve download speed.

Others:

Add more performance tests in the dfbench command.

Add more E2E tests and unit tests.

Documentation:

Restructure the documentation to make it easier for users to navigate.

Enhance the landing page UI.

AI Infrastructure:

Optimize large file distribution within the infrastructure.

Optimize handling of a large number of small I/Os for Nydus.

---

> 完整与最新内容以官方文档为准：[v2.3](https://d7y.io/docs/next/roadmap-v2.3/)
