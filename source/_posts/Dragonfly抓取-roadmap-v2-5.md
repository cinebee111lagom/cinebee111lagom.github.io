---
title: Dragonfly 抓取：v2.5
date: 2026-09-14 10:16:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/roadmap-v2.5/>

---

This document outlines the roadmap for Dragonfly v2.5, focusing on performance optimization,
enhanced functionality, and expanded use cases in AI/ML workloads. Dragonfly v2.5 is scheduled
for release on June 30, 2026.

## Core Components

### Manager

Enhance service performance and resource utilization while reducing CPU/Memory overhead.

Implement visualization for Persistent Task/Cache Task features.

Enhance user experience and UI design in the Manager Console.

### Scheduler

Enhance service performance and resource utilization while reducing CPU/Memory overhead.

Optimize the scheduling algorithm to improve bandwidth utilization in the P2P network.

### Client

Enhance service performance and resource utilization while reducing CPU/Memory overhead.

Implement Dfstore command for persistent task.

## Service Quality

Implement a client-side download task queue to prevent too many concurrent downloads.

Implement circuit breakers and rate limiting for each component to prevent cascading failures during sudden traffic spikes.

Centralized rate limiting for download tasks and back-to-origin traffic at the cluster level to prevent excessive
load on the origin.

Support emergency plans and implement service degradation for specified requests.

## File Distribution

Implement a bandwidth-aware negotiation protocol to distribute requests across multiple parent nodes,
preventing single-parent bottlenecks.

Optimize the Dragonfly Injector (Webhook) to support injecting the Dragonfly download tool into containers,
thereby improving ease of use in cloud-native environment.

## AI Agent

Enhanced Snapshotter's snapshot and restore performance.

## Others

### Observability

Improve and refine the monitoring metrics system.

Optimize the alerting mechanism and enhance issue diagnosis capabilities.

### Testing

Add more E2E tests and unit tests.

## Documentation

Enhance the landing page UI.

Add more documentation on system interactions and implementation details.

## Nydus

### Testing

Containerize smoke tests.

The unit test coverage for medium to large PRs should not be lower than the current project coverage rate.

### Core Components

#### Nydusd

Integrate Dragonfly SDK to request Dragonfly cache service.

RAFS V6 fuse and EROFS switching. When all local cached blob files exist, consider switching to EROFS to reduce fuse overhead.

Solution for nydusd token permanent expiration, consider supporting hot update capability for configuration files and auth.

Remove support for external volume for modelpack. This solution is no longer in use, so remove related code.

#### Snapshotter

snapshotter helm chart migration

#### Nydusify

support compacting image on commit

### Agent Sandbox

Best practice documentation for using nydus in agent sandbox scenarios.

---

> 完整与最新内容以官方文档为准：[v2.5](https://d7y.io/docs/next/roadmap-v2.5/)
