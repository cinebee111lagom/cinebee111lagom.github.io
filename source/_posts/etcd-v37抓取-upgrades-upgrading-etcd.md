---
title: etcd v3.7 抓取：Upgrading etcd clusters and applications
date: 2026-09-13 10:09:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/upgrades/upgrading-etcd/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/upgrades/upgrading-etcd/>

---

This section contains documents specific to upgrading etcd clusters and applications.

## Upgrade policy

Before upgrading, note that etcd only supports the following two upgrade cases:

Patch upgrade:
Upgrading between patch releases within the same minor version (e.g. 3.7.0 - 3.7.1).

Minor upgrade:
Upgrading one minor version at a time (e.g. 3.6 - 3.7). Upgrades that skip a minor version are not supported and will likely fail. Update to the most recent patch version before upgrading to the next minor version.

## Upgrading an etcd v3.x cluster

Upgrade etcd from 3.0 to 3.1

Upgrade etcd from 3.1 to 3.2

Upgrade etcd from 3.2 to 3.3

Upgrade etcd from 3.3 to 3.4

Upgrade etcd from 3.4 to 3.5

Upgrade etcd from 3.5 to 3.6

Upgrade etcd from 3.6 to 3.7

## Upgrading from etcd v2.3

Upgrade a v2.3 cluster to v3.0

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Upgrading etcd clusters and applications](https://etcd.io/docs/v3.7/upgrades/upgrading-etcd/)
