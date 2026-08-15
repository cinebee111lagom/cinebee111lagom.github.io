---
title: Dragonfly 高级：Preheat 预热
date: 2026-09-08 10:50:00
tags:
  - Dragonfly
  - Preheat
  - 进阶
categories:
  - Dragonfly 进阶指南
---

预热：提前把文件/镜像拉到 Seed 或 Peer，使后续下载直接命中 P2P 缓存。

## 按部署模型

| 模型 | 方式 |
|------|------|
| 无 Manager | `dfctl task preheat` 调 Scheduler gRPC |
| 有 Manager | Open API 或 Web Console 创建预热 Job |

## dfctl 示例

```shell
dfctl task preheat https://example.com/file.txt --scheduler-endpoint http://scheduler-service:8002
dfctl task preheat oci://docker.io/library/alpine:3.19 --scheduler-endpoint http://scheduler-service:8002
```

`--scope`：`single_seed_peer` / `all_seed_peers`（默认）/ `all_peers`。

> 官方文档：[Preheat](https://d7y.io/docs/next/advanced-guides/preheat/)

