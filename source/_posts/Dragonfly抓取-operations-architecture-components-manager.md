---
title: Dragonfly 抓取：Manager
date: 2026-09-14 09:12:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/architecture/components/manager/>

---

It plays the role of Manager in the multi-P2P cluster deployment process.
Used to manage the dynamic configuration that each module depends on,
and provide keepalive and metrics functions.

The Manager is optional at deployment. If the Manager is not deployed, the Scheduler and
Client load the dynamic configuration from the local
dynconfig.yaml
file instead of
fetching it from the Manager, refer to
Deployment Models
.

## Features

Stores dynamic configuration for consumption by seed peer cluster, Scheduler cluster and Client.

Maintain the relationship between seed peer cluster and Scheduler cluster.

Provide async task management features for image preheat combined with harbor.

Keepalive with Scheduler instance and seed peer instance.

Filter the optimal Scheduler cluster for Client.

Provides a visual console, which is helpful for users to manage the P2P cluster.

Peer features are configurable. For example, you can allow the peer to be downloaded and prevent the peer from being uploaded.

Clear P2P task cache.

Display P2P traffic distribution.

Peer information display, including CPU, Memory, etc.

## Relationship

Seed peer cluster and Scheduler cluster have a
1:1
relationship

Seed peer cluster and Seed peer instance have a
1:N
relationship

Scheduler cluster and Scheduler instance have a
1:N
relationship

## Manage multiple P2P networks

Manager can manage multiple P2P networks.
Usually, a P2P network includes a Scheduler cluster, a seed peer cluster and many dfdaemons.
The service network must be available in a P2P network.

---

> 完整与最新内容以官方文档为准：[Manager](https://d7y.io/docs/next/operations/architecture/components/manager/)
