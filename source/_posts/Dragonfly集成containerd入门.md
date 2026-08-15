---
title: Dragonfly 集成 containerd 入门
date: 2026-09-07 10:40:00
tags:
  - Dragonfly
  - containerd
  - 入门
categories:
  - Dragonfly 新手入门
---

containerd 是最常见的运行时集成目标：通过配置 registry mirror / proxy，把镜像拉取导向 Dragonfly Peer。

## 目标

- kubelet/containerd 拉镜像走 P2P
- 对业务 Pod 无侵入

## 落地要点

- 配置 hosts.toml 或 mirror 指向 dfdaemon proxy
- 验证 HTTPS 证书与私有仓库鉴权
- 对比开启前后：Registry 出网与节点拉取耗时

## 验收

- 同镜像多节点并发拉取，源站带宽显著下降
- 失败时有回源兜底，不阻断发版

> 官方文档：[containerd](https://d7y.io/docs/next/operations/integrations/container-runtime/containerd/)

