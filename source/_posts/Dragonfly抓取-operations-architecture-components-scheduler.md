---
title: Dragonfly 抓取：Scheduler
date: 2026-09-14 09:13:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/architecture/components/scheduler/>

---

Scheduler selects the optimal parent peer for current peer to be downloaded
and triggers the seed peer back-to-source download or Client back-to-source download at the appropriate time.

## Features

Based on the multi-feature intelligent scheduling system selects the optimal parent peer.

Build a scheduling directed acyclic graph for the P2P cluster.

Remove abnormal peer based on peer multi-feature evaluation results.

In the case of scheduling failure, notice peer back-to-source download.

Provide metadata storage to support file writing and seeding.

## Scheduling

Scheduler maintains task, peer and host resources.

Peer: a download task for Client

Host: host information for Client, host and peer have a
1:N
relationship

Task: a download task, task and peer have a
1:N
relationship

The scheduling process is actually to build a directed acyclic graph according to the peer's load.

### Load-Aware Scheduling Algorithm

A two-stage scheduling algorithm combining central scheduling with node-level secondary scheduling to
optimize P2P download performance based on real-time load awareness.

#### Architecture

#### Stage 1: Central Scheduling

The Scheduler evaluates and returns the top N parent for concurrent piece downloads.

```
TotalScore = (IDCAffinityScore × 0.2) + (LocationAffinityScore × 0.1) + (LoadQualityScore × 0.6) + (HostTypeScore × 0.1)
```

```
LoadQualityScore = (PeakBandwidthUsage × 0.5) + (BandwidthDurationRatio × 0.3) + (ConcurrentEfficiency × 0.2)
```

#### Stage 2: Secondary Scheduling

Real-time parent selection performed by the peer for each piece based on load quality.

While the central scheduler provides initial candidate selection, the Parent Selector enables dynamic adaptation to:

Real-time load: Network conditions fluctuate rapidly during downloads.

Reduced central load: Distributes scheduling decisions across peers.

Lower latency: Local decisions avoid round-trip delays to central scheduler.

---

> 完整与最新内容以官方文档为准：[Scheduler](https://d7y.io/docs/next/operations/architecture/components/scheduler/)
