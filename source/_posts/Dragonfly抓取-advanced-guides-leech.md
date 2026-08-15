---
title: Dragonfly 抓取：Leech
date: 2026-09-14 09:38:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/leech/>

---

This document explains that peers download files or data but do not upload anything.

If the user configures the client to disable sharing, it will become a leech.
Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
,
refer to
dfdaemon config
.

```
upload
:
# disableShared indicates whether disable to share data for other peers.
disableShared
:
true
```

---

> 完整与最新内容以官方文档为准：[Leech](https://d7y.io/docs/next/advanced-guides/leech/)
