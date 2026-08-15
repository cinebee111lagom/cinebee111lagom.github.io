---
title: Volcano 抓取：Task Topology 插件用户指南
date: 2026-09-14 09:54:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_task_topology_plugin>

---

## 环境准备

### 安装 Volcano

请参考
安装指南
安装 Volcano。

### 更新调度器 ConfigMap

安装完成后，更新调度器配置：

```
kubectl edit configmap -n volcano-system volcano-scheduler-configmap
```

在 ConfigMap 中注册
task-topology
插件：

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
actions: "enqueue, allocate, backfill"
tiers:
- plugins:
- name: priority
- name: gang
- name: conformance
- plugins:
- name: drf
- name: predicates
- name: task-topology
arguments:
task-topology.weight: 10
- name: proportion
- name: nodeorder
- name: binpack
```

### 运行 Job

以 TensorFlow Job 为例。

#### 安装 kubeflow/tf-operator

请参考
Kubeflow 入门指南
安装 Kubeflow（含 tf-operator）。

#### 编辑 TFJob YAML

在 Volcano Job 或 TensorFlow Job 中添加如下格式的注解：
affinity
：表示 Task 之间存在关联，应尽量调度到同一节点；
anti-affinity
：表示 Task 之间无关联，应尽量调度到不同节点；
task-order
：表示 Task 的调度顺序。例如
ps,worker
表示先调度
ps
，全部
ps
分配完成后再调度
worker
。
该注解为可选字段。
volcano.sh/task-topology-affinity
:
"ps,worker;ps,evaluator"
volcano.sh/task-topology-anti-affinity
:
"ps;worker,chief;chief,evaluator"
volcano.sh/task-topology-task-order
:
"ps,worker,chief,evaluator"

affinity
：表示 Task 之间存在关联，应尽量调度到同一节点；

anti-affinity
：表示 Task 之间无关联，应尽量调度到不同节点；

task-order
：表示 Task 的调度顺序。例如
ps,worker
表示先调度
ps
，全部
ps
分配完成后再调度
worker
。
该注解为可选字段。
volcano.sh/task-topology-affinity
:
"ps,worker;ps,evaluator"
volcano.sh/task-topology-anti-affinity
:
"ps;worker,chief;chief,evaluator"
volcano.sh/task-topology-task-order
:
"ps,worker,chief,evaluator"

task-order
：表示 Task 的调度顺序。例如
ps,worker
表示先调度
ps
，全部
ps
分配完成后再调度
worker
。
该注解为可选字段。

```
volcano.sh/task-topology-affinity
:
"ps,worker;ps,evaluator"
volcano.sh/task-topology-anti-affinity
:
"ps;worker,chief;chief,evaluator"
volcano.sh/task-topology-task-order
:
"ps,worker,chief,evaluator"
```

---

> 完整与最新内容以官方文档为准：[Task Topology 插件用户指南](https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_task_topology_plugin)
