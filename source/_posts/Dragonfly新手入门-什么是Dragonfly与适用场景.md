---
title: Dragonfly 新手入门：什么是 Dragonfly 与适用场景
date: 2026-09-07 09:00:00
tags:
  - Dragonfly
  - P2P
  - 入门
categories:
  - Dragonfly 新手入门
---

**Dragonfly** 是基于 P2P 的云原生文件与镜像分发系统（CNCF Graduated），用于高效、稳定、低成本地分发容器镜像、OCI Artifact、模型、依赖包等。

## 核心能力

| 能力 | 说明 |
|------|------|
| P2P 加速 | 利用 Peer 空闲带宽提速 |
| 非侵入集成 | 对接 containerd / CRI-O / Harbor / AI 工具链 |
| 负载感知调度 | 中心调度 + 节点侧二次调度 |
| 一致性 | 分片下载后保证文件一致 |
| 异常隔离 | 服务 / Peer / Task 级隔离 |

## 四大组件

| 组件 | 角色 |
|------|------|
| Manager | 可选控制面：控制台、动态配置、多集群 |
| Scheduler | 为下载 Peer 选择最优 Parent |
| Seed Peer | 可选根 Peer，可回源并分发 |
| Peer | 上传/下载能力（dfdaemon） |

## 适用场景

- 大规模节点同时拉镜像导致源站/Registry 打满
- AI 模型与数据集集群内分发
- CI / 边缘 / 多集群镜像同步与预热

> 官方文档：[Introduction](https://d7y.io/docs/next/)

