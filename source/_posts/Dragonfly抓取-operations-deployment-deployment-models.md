---
title: Dragonfly 抓取：Deployment Models
date: 2026-09-14 09:15:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/deployment/deployment-models/>

---

Dragonfly supports multiple deployment models, and the available features depend on
which components are deployed. Choose the deployment model according to the features you need.

## Lightweight deployment

Deploy the Scheduler, Seed Client and Client only, without the Manager and its MySQL and
Redis dependencies. The scheduler and client load the dynamic configuration from the local
dynconfig.yaml
file mounted as a ConfigMap instead of fetching it from the Manager, and
clients discover schedulers via the scheduler headless service, refer to
scheduler config
and
dfdaemon config
.

It is the recommended deployment model for most scenarios that only need the P2P
distribution capabilities (e.g., small Kubernetes clusters, edge environments, or CI systems).
It supports the task distribution and preheating via
dfctl
, refer to
Lightweight Deployment
and
Preheat
.

## Lightweight deployment with Redis

Deploy Redis in addition to the lightweight deployment, and configure the scheduler's
database.redis.addrs
to use it. The persistent task and persistent cache task features
store metadata in Redis, so they are only available when the scheduler is deployed with Redis.

For the helm charts, set
redis.enable
to
true
to deploy Redis with the chart, or set
externalRedis.addrs
to use an existing Redis, refer to
Create Dragonfly cluster with Redis based on helm charts
.

## Deployment with Manager

Deploy the Manager along with MySQL and Redis in addition to the Scheduler, Seed Client and
Client. The Manager provides the control plane of Dragonfly: the web console, Open API,
preheating jobs and multi-cluster management, refer to
Deployment with Manager on Kubernetes
and
Deployment with Manager on Multi-cluster Kubernetes
.

## Feature Matrix

---

> 完整与最新内容以官方文档为准：[Deployment Models](https://d7y.io/docs/next/operations/deployment/deployment-models/)
