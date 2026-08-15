---
title: Dragonfly 抓取：v2.2
date: 2026-09-14 10:13:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/roadmap-v2.2/>

---

Manager:

Add clearing P2P task cache.

Peer information display, including CPU, Memory, etc.

Scheduler:

Optimize scheduling algorithm and improve bandwidth utilization in the P2P network.

Client:

Client written in Rust, reduce CPU usage and Memory usage.

Others:

Defines the V2 of the P2P transfer protocol.

Document:

Restructure the document to make it easier for users to use.

Enhance the landing page UI.

AI Infrastructure:

Supports Triton Inference Server to accelerate model distribution, refer to
dragonfly-repository-agent
.

Supports TorchServer to accelerate model distribution, refer to
document
.

Supports HuggingFace to accelerate model distribution and dataset distribution, refer to
document
.

Supports Git LFS to accelerate file distribution, refer to
document
.

Supports JuiceFS to accelerate file downloads from object storage, JuiceFS read requests via
peer proxy and write requests via the default client of object storage.

Supports Fluid to accelerate model distribution.

Support AI infrastructure to efficiently distribute models and datasets, and integrated with the AI ecosystem.

---

> 完整与最新内容以官方文档为准：[v2.2](https://d7y.io/docs/next/roadmap-v2.2/)
