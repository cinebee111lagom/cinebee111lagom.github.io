---
title: Dragonfly 抓取：v2.1
date: 2026-09-14 10:12:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/roadmap-v2.1/>

---

Manager:

Console
v1.0.0
is released and it provides
a new console for users to operate Dragonfly.

Provides the ability to control the features of the scheduler in the manager. If the scheduler preheat feature is
not in feature flags, then it will stop providing the preheating in the scheduler.

Add personal access tokens feature in the manager and personal access token
contains your security credentials for the restful open api.

Add TLS config to manager rest server.

Add cluster in the manager and the cluster contains a scheduler cluster and a seed peer cluster.

Use unscoped delete when destroying the manager's resources.

Add uk_scheduler index and uk_seed_peer index in the table of the database.

Remove security domain feature and security feature in the manager.

Add advertise port config.

Scheduler:

Add network topology feature and it can probe the network latency between peers, providing better scheduling capabilities.

Scheduler adds database field in config and moves the redis config to database field.

Fix filtering and evaluation in scheduling. Since the final length of the filter is
the candidateParentLimit used, the parents after the filter is wrong.

Fix storage cannot write records to file when bufferSize is zero.

Add advertise port config.

Fix fsm changes state failed when register task.

Client:

Dfstore adds GetObjectMetadatas and CopyObject to supports using Dragonfly as the JuiceFS backend.

Fix dfdaemon fails to start when there is no available scheduler address.

Fix object downloads failed by dfstore when dfdaemon enabled concurrent.

Replace net.Dial with grpc health check in dfdaemon.

Others:

A third party security audit was performed by Trail of Bits, you can see the
full report
.

Hiding sensitive information in logs, such as the token in the header.

---

> 完整与最新内容以官方文档为准：[v2.1](https://d7y.io/docs/next/roadmap-v2.1/)
