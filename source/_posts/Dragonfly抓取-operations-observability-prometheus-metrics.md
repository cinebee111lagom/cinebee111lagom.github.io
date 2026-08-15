---
title: Dragonfly 抓取：Prometheus Metrics
date: 2026-09-14 09:33:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/observability/prometheus-metrics/>

---

This doc contains all the metrics that Dragonfly components currently support.
Now we support metrics for Client, Seed Client, Scheduler and Manager.
The metrics path is fixed to
/metrics
. The following metrics are exported.

## Client

GRPC metrics are exposed via
go-grpc-prometheus
.

## Scheduler

GRPC metrics are exposed via
go-grpc-prometheus
.

## Manager

GRPC metrics are exposed via
go-grpc-prometheus
.

---

> 完整与最新内容以官方文档为准：[Prometheus Metrics](https://d7y.io/docs/next/operations/observability/prometheus-metrics/)
