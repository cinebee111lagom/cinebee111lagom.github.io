---
title: Dragonfly 集成 CRI-O 入门
date: 2026-09-07 11:00:00
tags:
  - Dragonfly
  - CRI-O
  - 入门
categories:
  - Dragonfly 新手入门
---

CRI-O 集群同样可通过 registry 镜像/代理接入 Dragonfly。

## 要点

- 在 CRI-O registries 配置中指向 Peer Proxy
- 与 containerd 一样关注 TLS 与私有仓鉴权
- 滚动节点时分批验证，避免全网同时切流

## 排障

- 看 Peer 侧 proxy 请求指标与失败率
- 确认 CRI-O 是否仍直连上游

> 官方文档：[CRI-O](https://d7y.io/docs/next/operations/integrations/container-runtime/cri-o/)

