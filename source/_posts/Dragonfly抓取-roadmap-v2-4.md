---
title: Dragonfly 抓取：v2.4
date: 2026-09-14 10:15:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/roadmap-v2.4/>

---

Manager

Optimize memory and CPU usage.

Regularly clean up inactive schedulers and seed peers.

Support specifying scheduler cluster ID in client configuration, allowing the client to connect to a specific
scheduler cluster.

Scheduler

Implement scheduler-aware peer bandwidth scheduling.

Optimize the scheduling algorithm to improve bandwidth utilization in the P2P network.

Client

Support RDMA for faster network transmission in the P2P network, enhancing the loading of
AI inference models into memory.

Support TCP and QUIC protocols for downloading files, allowing users to choose the protocol that best suits their needs.

Optimize file transfer speed in the P2P network.

Encrypted storage of downloaded content offers a more secure solution.

Support selecting the optimal parent for downloading based on QoS (Quality of Service) metrics.

Others

Add auto injection webhook and integration with helm chart for easier deployment and management.

Add more E2E tests and unit tests.

Documentation

Restructure the documentation to make it easier for users to navigate.

Enhance the landing page UI.

Add more documentation on system interactions and implementation details.

AI Infrastructure

Optimize large file distribution within the infrastructure.

Optimize handling of a large number of small I/Os for Nydus.

---

> 完整与最新内容以官方文档为准：[v2.4](https://d7y.io/docs/next/roadmap-v2.4/)
