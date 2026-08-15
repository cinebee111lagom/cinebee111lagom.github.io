---
title: Dragonfly 抓取：Persistent Cache Task
date: 2026-09-14 09:10:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/concepts/persistent-cache-task/>

---

It designs to provide persistent caching for tasks. This tool can import file and export file in P2P network. The solution is specifically engineered for high-speed read and write operations. This makes it particularly advantageous for scenarios involving large files, such as machine learning model checkpoints, where rapid, reliable access and distribution across the network are critical for training and inference workflows. By leveraging P2P distribution and persistent caching, dfcache significantly reduces I/O bottlenecks and accelerates the lifecycle of large data assets.

## Dfcache

Use dfcache to import files, please refer to
dfcache
.

```
$ dfcache import /tmp/file.txt
⣷ Done: e2d0fe1585a63ec6009c8016ff8dda8b17719a637405a4e23c0ff81339148249
```

Use dfcache to export files.

```
$ dfcache export e2d0fe1585a63ec6009c8016ff8dda8b17719a637405a4e23c0ff81339148249 -O /tmp/file.txt
[00:00:00] [############################################################] 8.73 KiB/8.73 KiB (7.30 MiB/s, 0.0s)
```

## Console

View persistent cache task details or delete a persistent cache task, please refer to
persistent cache task
.

---

> 完整与最新内容以官方文档为准：[Persistent Cache Task](https://d7y.io/docs/next/concepts/persistent-cache-task/)
