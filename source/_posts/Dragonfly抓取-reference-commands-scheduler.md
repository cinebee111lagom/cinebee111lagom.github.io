---
title: Dragonfly 抓取：Scheduler
date: 2026-09-14 09:57:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/reference/commands/scheduler/>

---

Scheduler is a long-running process which receives
and manages download tasks from the client,
notify the seed peer to return to the source, generate and maintain a
P2P network during the download process,
and push suitable download nodes to the client

## Usage

```
scheduler [flags]
scheduler [command]
```

## Available Commands

```
completion  generate the autocompletion script for the specified shell
doc         generate documents
help        Help about any command
plugin      show plugin
version     show version
```

## Options

```
--config string         the path of configuration file with yaml extension name, default is /etc/dragonfly/scheduler.yaml, it can also be set by env var: SCHEDULER_CONFIG
--console               whether logger output records to the stdout
-h, --help                  help for scheduler
```

## Log

```
1. set option --console if you want to print logs to Terminal
2. log path: /var/log/dragonfly/scheduler/
```

---

> 完整与最新内容以官方文档为准：[Scheduler](https://d7y.io/docs/next/reference/commands/scheduler/)
