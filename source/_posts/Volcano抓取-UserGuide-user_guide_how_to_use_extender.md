---
title: Volcano 抓取：Extender 用户指南
date: 2026-09-14 09:38:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_extender>

---

### 安装 Volcano

#### 1. 从源码安装

请参考
安装指南
安装 Volcano。

#### 2. 部署 Extender

将 Extender 部署到 Kubernetes 集群。Extender 需要对外暴露域名或 IP 地址，并提供可调用的 verb。

#### 3. 更新 Volcano 配置

```
kubectl edit cm -n volcano-system volcano-scheduler-configmap
```

可通过
设计文档
查看各参数含义。

```
kind
:
ConfigMap
apiVersion
:
v1
metadata
:
name
:
volcano
-
scheduler
-
configmap
namespace
:
volcano
-
system
data
:
volcano-scheduler.conf
:
|
actions: "reclaim, allocate, backfill, preempt"
tiers:
- plugins:
- name: priority
- name: gang
- name: conformance
- plugins:
- name: drf
- name: predicates
- name: extender
arguments:
extender.urlPrefix: http://127.0.0.1:8713
extender.httpTimeout: 100ms
extender.onSessionOpenVerb: onSessionOpen
extender.onSessionCloseVerb: onSessionClose
extender.predicateVerb: predicate
extender.prioritizeVerb: prioritize
extender.preemptableVerb: preemptable
extender.reclaimableVerb: reclaimable
extender.queueOverusedVerb: queueOverused
extender.jobEnqueueableVerb: jobEnqueueable
extender.ignorable: true
```

### 验证 Extender 是否生效

在日志中可看到类似：
Initialize extender plugin with configuration : {your configuration}

---

> 完整与最新内容以官方文档为准：[Extender 用户指南](https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_extender)
