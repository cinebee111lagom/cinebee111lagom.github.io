---
title: Dragonfly 集成 Singularity 入门
date: 2026-09-07 10:50:00
tags:
  - Dragonfly
  - Singularity
  - 入门
categories:
  - Dragonfly 新手入门
---

HPC / 科研场景常用 Singularity（Apptainer）。Dragonfly 可加速其镜像/制品分发。

## 适用

- 集群节点批量拉取同一 SIF / OCI 制品
- 共享存储压力大、希望改走 P2P

## 实践

- 按官方文档把下载路径接到 Peer
- 统一版本与校验，避免混用直连与代理导致缓存键不一致

> 官方文档：[Singularity](https://d7y.io/docs/next/operations/integrations/container-runtime/singularity)

