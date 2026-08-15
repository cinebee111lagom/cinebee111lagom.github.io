---
title: Dragonfly 抓取：Tracing
date: 2026-09-14 09:34:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/observability/tracing/>

---

This document provides a guide on how to set up tracing for Dragonfly, which is
essential for monitoring and debugging distributed systems.

### Setup Jaeger

Set up a Jaeger instance to collect and visualize tracing data from Dragonfly components, refer to the
Jaeger documentation
for detailed instructions.

```
docker run --rm --name jaeger \
-p 16686:16686 \
-p 4317:4317 \
-p 4318:4318 \
-p 5778:5778 \
-p 9411:9411 \
jaegertracing/jaeger:2.3.0
```

### Configure the tracing endpoint in Dragonfly

#### Add tracing configuration as follows(in Manager, Scheduler and Dfdaemon)

```
tracing
:
# Protocol to use for tracing.
protocol
:
grpc
# Jaeger endpoint url, like: jaeger.dragonfly.svc:4317.
endpoint
:
jaeger.dragonfly.svc
:
4317
```

#### Access the Jaeger UI

Jaeger will automatically collect the tracing data from Dragonfly components.
You can access the Jaeger UI at
http://localhost:16686
to visualize the traces.

---

> 完整与最新内容以官方文档为准：[Tracing](https://d7y.io/docs/next/operations/observability/tracing/)
