---
title: Dragonfly 集成 Podman 入门
date: 2026-09-08 09:50:00
tags:
  - Dragonfly
  - Podman
  - 入门
categories:
  - Dragonfly 新手入门
---

Podman 环境同样可把镜像拉取接入 Dragonfly Proxy/P2P。

## 实践

- 配置 registries.conf / 代理指向 Peer
- rootless 场景注意权限与端口可达性
- 用同一测试镜像对比直连与经 Dragonfly 的耗时与源站流量

> 官方文档：[Podman](https://d7y.io/docs/next/operations/integrations/container-runtime/podman/)

