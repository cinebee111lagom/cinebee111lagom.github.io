---
title: Volcano 抓取：Cooldown Protection（CDP）插件用户指南
date: 2026-09-14 09:36:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_cdp_plugin>

---

## 背景

在弹性训练或弹性推理场景下，可抢占 Job 的 Pod 可能被反复抢占或恢复运行。若未设置冷却保护，Pod 刚启动不久可能再次被抢占，导致服务稳定性下降。

因此 Volcano 提供
cdp
插件，确保可抢占 Job 的 Pod 至少能按用户设定的时间运行一段时间。

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

在启用
preempt
action 的同时，于 ConfigMap 中注册
cdp
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
actions: "enqueue, allocate, preempt, backfill"
tiers:
- plugins:
- name: priority
- name: gang
- name: conformance
- name: cdp
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

以下以一个简单的 Volcano Job 为例。原始 Job 包含
ps
与
worker
两个 Task：

```
apiVersion
:
batch.volcano.sh/v1alpha1
kind
:
Job
metadata
:
name
:
test
-
job
spec
:
minAvailable
:
3
schedulerName
:
volcano
priorityClassName
:
high
-
priority
plugins
:
ssh
:
[
]
env
:
[
]
svc
:
[
]
maxRetry
:
5
queue
:
default
volumes
:
-
mountPath
:
"/myinput"
-
mountPath
:
"/myoutput"
volumeClaimName
:
"testvolumeclaimname"
volumeClaim
:
accessModes
:
[
"ReadWriteOnce"
]
storageClassName
:
"my-storage-class"
resources
:
requests
:
storage
:
1Gi
tasks
:
-
replicas
:
6
name
:
"worker"
template
:
metadata
:
name
:
worker
spec
:
containers
:
-
image
:
nginx
imagePullPolicy
:
IfNotPresent
name
:
nginx
resources
:
requests
:
cpu
:
"1"
restartPolicy
:
OnFailure
-
replicas
:
2
name
:
"ps"
template
:
metadata
:
name
:
ps
spec
:
containers
:
-
image
:
nginx
imagePullPolicy
:
IfNotPresent
name
:
nginx
resources
:
requests
:
cpu
:
"1"
restartPolicy
:
OnFailure
```

#### 编辑 Volcano Job YAML

按以下格式在 Volcano Job 中添加注解：
volcano.sh/preemptable
：表示 Job 或 Task 可被抢占；
volcano.sh/cooldown-time
：表示整个 Job 或指定 Task 的冷却时间。合法时间单位包括
ns
、
us
（或
µs
）、
ms
、
s
、
m
、
h
。
volcano.sh/preemptable
:
"true"
volcano.sh/cooldown-time
:
"600s"

volcano.sh/preemptable
：表示 Job 或 Task 可被抢占；

volcano.sh/cooldown-time
：表示整个 Job 或指定 Task 的冷却时间。合法时间单位包括
ns
、
us
（或
µs
）、
ms
、
s
、
m
、
h
。
volcano.sh/preemptable
:
"true"
volcano.sh/cooldown-time
:
"600s"

volcano.sh/cooldown-time
：表示整个 Job 或指定 Task 的冷却时间。合法时间单位包括
ns
、
us
（或
µs
）、
ms
、
s
、
m
、
h
。

```
volcano.sh/preemptable
:
"true"
volcano.sh/cooldown-time
:
"600s"
```

示例 1

在 Job 级别添加注解，则
ps
与
worker
均可被抢占，且均受冷却时间保护。

```
apiVersion
:
batch.volcano.sh/v1alpha1
kind
:
Job
metadata
:
name
:
test
-
job
annotations
:
volcano.sh/preemptable
:
"true"
volcano.sh/cooldown-time
:
"600s"
spec
:
...
# 以下保持不变
```

示例 2

仅在指定 Task 上添加注解。如下所示，仅
worker
可被抢占并享有冷却时间保护。

```
apiVersion
:
batch.volcano.sh/v1alpha1
kind
:
Job
metadata
:
name
:
test
-
job
spec
:
minAvailable
:
3
schedulerName
:
volcano
priorityClassName
:
high
-
priority
plugins
:
ssh
:
[
]
env
:
[
]
svc
:
[
]
maxRetry
:
5
queue
:
default
volumes
:
-
mountPath
:
"/myinput"
-
mountPath
:
"/myoutput"
volumeClaimName
:
"testvolumeclaimname"
volumeClaim
:
accessModes
:
[
"ReadWriteOnce"
]
storageClassName
:
"my-storage-class"
resources
:
requests
:
storage
:
1Gi
tasks
:
-
replicas
:
6
name
:
"worker"
template
:
metadata
:
name
:
worker
annotations
:
# 在 Task 上添加注解
volcano.sh/preemptable
:
"true"
volcano.sh/cooldown-time
:
"600s"
spec
:
containers
:
-
image
:
nginx
imagePullPolicy
:
IfNotPresent
name
:
nginx
resources
:
requests
:
cpu
:
"1"
restartPolicy
:
OnFailure
-
replicas
:
2
name
:
"ps"
template
:
metadata
:
name
:
ps
spec
:
containers
:
-
image
:
nginx
imagePullPolicy
:
IfNotPresent
name
:
nginx
resources
:
requests
:
cpu
:
"1"
restartPolicy
:
OnFailure
```

---

> 完整与最新内容以官方文档为准：[Cooldown Protection（CDP）插件用户指南](https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_cdp_plugin)
