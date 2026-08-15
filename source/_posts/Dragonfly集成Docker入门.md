---
title: Dragonfly 集成 Docker 入门
date: 2026-09-08 09:30:00
tags:
  - Dragonfly
  - Docker
  - 入门
categories:
  - Dragonfly 新手入门
---

Docker 引擎可通过 registry mirror / HTTP 代理将拉取导向 Dragonfly Peer。

## 要点

- 配置 daemon 的 registry-mirrors 或代理指向 dfdaemon
- 私有仓鉴权与 TLS 证书一并验证
- 与 containerd 方案类似：目标是无侵入加速 `docker pull`

> 官方文档：[Docker](https://d7y.io/docs/next/operations/integrations/container-runtime/docker/)

