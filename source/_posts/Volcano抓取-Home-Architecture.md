---
title: Volcano 抓取：架构
date: 2026-09-14 09:01:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/Home/Architecture>

---

## 架构概览

Volcano与Kubernetes天然兼容，并为高性能计算而生。它遵循Kubernetes的设计理念和风格。

Volcano由scheduler、controllermanager、admission和vcctl组成:

## (Scheduler)

Volcano scheduler通过一系列的action和plugin调度Job，并为它找到一个最适合的节点。与Kubernetes default-scheduler相比，Volcano与众不同的
地方是它支持针对Job的多种调度算法。

## (ControllerManager)

Volcano controllermanager管理CRD资源的生命周期。它主要由
Queue ControllerManager
、
PodGroupControllerManager
、
VCJob
ControllerManager
构成。

## (Admission)

Volcano admission负责对CRD API资源进行校验。

## (Vcctl)

Volcano vcctl是Volcano的命令行客户端工具。

---

> 完整与最新内容以官方文档为准：[架构](https://volcano.sh/zh-Hans/docs/Home/Architecture)
