---
title: Volcano 文档：简介与由来
date: 2026-09-10 09:00:00
tags:
  - Volcano
  - 入门
categories:
  - Volcano 文档导读
---

Volcano 是 CNCF 下基于 Kubernetes 的**容器批量计算平台**，面向机器学习、大数据、科学计算、渲染等高性能工作负载。

## 解决什么问题

- 调度算法多样性与性能
- 无缝对接主流计算框架
- 异构设备（GPU/NPU 等）调度

继承 Kubernetes 接口风格，可与现有 K8s 使用习惯共存。

## 能力速览

统一调度、Gang/Binpack/队列配额、GPU 虚拟化、网络拓扑感知、在离线混部、多集群、重调度与可观测性。

> 官方文档：[Introduction](https://volcano.sh/zh-Hans/docs/Home/Introduction)

