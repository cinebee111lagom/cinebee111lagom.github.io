---
title: Dragonfly 抓取：v2.6
date: 2026-09-14 10:17:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/roadmap-v2.6/>

---

This document outlines the roadmap for Dragonfly v2.6, focusing on performance optimization,
enhanced functionality, and expanded use cases in AI/ML workloads. Dragonfly v2.6 is scheduled
for release on December 31, 2026.

## Core Components

### Manager

Enhance service performance and resource utilization while reducing CPU/Memory overhead.

Enhance user experience and UI design in the Manager Console.

Support optionally removing the Manager dependency, reducing the minimum cluster deployment unit to Scheduler and Client.

### Scheduler

Enhance service performance and resource utilization while reducing CPU/Memory overhead.

Optimize the scheduling algorithm to improve bandwidth utilization in the P2P network.

### Client

Enhance service performance and resource utilization while reducing CPU/Memory overhead.

Implement a bandwidth-aware negotiation protocol to distribute requests across multiple parent nodes,
preventing single-parent bottlenecks.

Dfcache/Dfstore support to import persistent cache task to Dfdaemon in Node by UDS.

Implement RDMA-based distribution of the files.

Support cache task memory-level download tasks.

Support reflink to avoid unnecessary data copying.

## AI Model/Dataset Distribution

Writes use Direct IO, reads use Buffered IO.

Implement Python SDK to provide data distribution for AI Infrastructure.

## AI Agent

Ensure data reliability when asynchronously writing to object storage.

Implement Python SDK to support snapshotter for use in AI agent.

Explore integrating the Agent Sandbox, Gymnasium, etc.

## Others

### Observability

Improve and refine the monitoring metrics system.

Optimize the alerting mechanism and enhance issue diagnosis capabilities.

### Security

Implement encrypted data storage.

### Testing

Add more E2E tests and unit tests.

### Skills / Agent Capabilities

Add a Dragonfly skill to enable troubleshooting and diagnosis capabilities.

## Documentation

Enhance the landing page UI.

Add more documentation on system interactions and implementation details.

## Nydus

### Testing

Increase unit test coverage target to 60%. Consider leveraging agent capabilities.

### Core Components

#### Nydusd

Deprecate erofs+fscache solution and migrate to erofs+fanotify pre-hook solution.

#### Snapshotter

Further enhance observability. For example:
Collect statistics on nydusd image-related information.
Support Prometheus metrics collection.

Collect statistics on nydusd image-related information.

Support Prometheus metrics collection.

Regarding Containerd's issues related to multi-snapshotter switching, organize best practice documentation.
follow Containerd community progress

follow Containerd community progress

#### Nydus Image

Better support for image conversion from Nydus to OCI. Fix errors during reverse conversion of large images.

### Kata Container Support

Best practice documentation for using nydus in Kata Container scenarios.

### Skills / Agent Capabilities

Add a Dragonfly skill to enable troubleshooting and diagnosis capabilities.

---

> 完整与最新内容以官方文档为准：[v2.6](https://d7y.io/docs/next/roadmap-v2.6/)
