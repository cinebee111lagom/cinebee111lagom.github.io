---
title: Dragonfly 抓取：Manager
date: 2026-09-14 09:56:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/reference/commands/manager/>

---

Manager is a process that runs in the background
and plays the role of the brain of each subsystem cluster in Dragonfly.
It is used to manage the dynamic
configuration of each system module and provide functions
such as heartbeat keeping alive, monitoring the market, and product functions.

## Usage

```
manager [flags]
manager [command]
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
--config string         the path of configuration file with yaml extension name, default is /etc/dragonfly/manager.yaml, it can also be set by env var: MANAGER_CONFIG
--console               whether logger output records to the stdout
-h, --help                  help for manager
```

## Log

```
1. set option --console if you want to print logs to Terminal
2. log path: /var/log/dragonfly/manager/
```

---

> 完整与最新内容以官方文档为准：[Manager](https://d7y.io/docs/next/reference/commands/manager/)
