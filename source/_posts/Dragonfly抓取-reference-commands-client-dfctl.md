---
title: Dragonfly 抓取：Dfctl
date: 2026-09-14 10:01:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/reference/commands/client/dfctl/>

---

dfctl
is the command-line tool of Dragonfly used to manage tasks in client's local storage, including task,
persistent task and persistent cache task.

## Usage

### Task

List all tasks in client's local storage.

```
dfctl task ls
```

Delete a task in client's local storage.

```
dfctl task rm <ID>
```

Preheat a file task.

```
dfctl task preheat http://example.com/file.txt --scheduler-endpoint http://scheduler-service:8002
```

Preheat a image task.

```
dfctl task preheat oci://docker.io/library/nginx:latest --scheduler-endpoint http://scheduler-service:8002 --username <USERNAME>  --password <PASSWORD>
```

### Persistent Task

List all persistent tasks in client's local storage.

```
dfctl persistent-task ls
```

### Persistent Cache Task

List all persistent cache tasks in client's local storage.

```
dfctl persistent-cache-task ls
```

---

> 完整与最新内容以官方文档为准：[Dfctl](https://d7y.io/docs/next/reference/commands/client/dfctl/)
