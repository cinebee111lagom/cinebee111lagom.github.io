---
title: Volcano 抓取：Ascend vNPU 用户指南
date: 2026-09-14 09:42:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_vnpu>

---

## 简介

Volcano 支持两种用于共享 Ascend 设备的
vNPU 模式
：

### 1. MindCluster 模式

说明
：

MindCluster
（Ascend 官方集群调度组件）的早期版本需要对 Volcano 进行定制修改与重新编译，且仅支持 Volcano release 1.7 与 release 1.9，使用成本高，也难以使用较新的 Volcano 能力。

为此，我们已将 Ascend vNPU 的核心调度逻辑集成到 Volcano 原生
deviceshare
插件中；该插件面向 GPU、NPU 等异构资源的调度与共享。按本文步骤即可无缝使用 vNPU，同时保持与最新 Volcano 特性的兼容。

适用场景
：

Ascend 310 系列的 vNPU 集群
后续将支持更多芯片类型

### 2. HAMi 模式

说明
：

该模式由第三方社区 HAMi 开发；HAMi 也是
Volcano vGPU
特性的开发者。支持 Ascend 310 与 Ascend 910 的 vNPU，并可管理异构 Ascend 集群（集群内包含多种 Ascend 型号，例如 910A、910B2、910B3、310P）。

适用场景
：

Ascend 910 系列的 NPU 与 vNPU 集群
Ascend 310 系列的 NPU 与 vNPU 集群
异构 Ascend 集群

## 安装

启用 vNPU 调度时，需根据所选模式安装以下组件。

前置条件
：

Kubernetes >= 1.16
Volcano >= 1.14
ascend-docker-runtime
（HAMi 模式需要）

### 安装 Volcano

请参阅 Volcano 安装指南：

Volcano 快速入门

### 安装 ascend-device-plugin 及第三方组件

本步骤需根据所选 vNPU 模式安装不同的 ascend-device-plugin。MindCluster 模式还需安装 Ascend 提供的其他组件。

#### MindCluster 模式

请按
Ascend 官方文档
安装以下组件：

NodeD

Ascend Device Plugin

Ascend Docker Runtime

ClusterD

Ascend Operator

说明：
上文文档中的
ascend-volcano
无需安装，前置条件中已安装 Volcano 社区原生版本。

Ascend Device Plugin 配置调整：

安装
ascend-device-plugin
时，须在
device-plugin-310P-volcano-v{version}.yaml
中将
presetVirtualDevice
参数设为
"false"
，以启用 310P 的动态虚拟化：

```
...
args
:
[
"device-plugin"
,
"-useAscendDocker=true"
,
"-volcanoType=true"
,
"-presetVirtualDevice=false"
,
"-logFile=/var/log/mindx-dl/devicePlugin/devicePlugin.log"
,
"-logLevel=0"
,
]
...
```

更多细节请参阅
Ascend MindCluster 文档
。

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
- name: predicates
- name: deviceshare
arguments:
deviceshare.AscendMindClusterVNPUEnable: true   # enable ascend vnpu
configurations:
...
- name: init-params
arguments: {"grace-over-time":"900","presetVirtualDevice":"false"}  # to enable dynamic virtualization, presetVirtualDevice need to be set false
```

#### HAMi 模式

```
kubectl label node {ascend-node} ascend=on
```

```
kubectl apply -f https://raw.githubusercontent.com/Project-HAMi/ascend-device-plugin/refs/heads/main/ascend-device-configmap.yaml
```

```
kubectl apply -f https://raw.githubusercontent.com/Project-HAMi/ascend-device-plugin/refs/heads/main/ascend-device-plugin.yaml
```

更多信息请参阅
ascend-device-plugin 文档
。

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
- name: predicates
- name: deviceshare
arguments:
deviceshare.AscendHAMiVNPUEnable: true   # enable ascend vnpu
deviceshare.SchedulePolicy: binpack  # scheduling policy. binpack / spread
deviceshare.KnownGeometriesCMNamespace: kube-system
deviceshare.KnownGeometriesCMName: hami-scheduler-device
```

说明：
volcano-vgpu
有各自的
GeometriesCMName
与
GeometriesCMNamespace
。若在同一 Volcano 集群中同时使用 vNPU 与 vGPU，需合并两侧的 ConfigMap 并在此处配置。

## 使用

用法因所选模式而异。

### MindCluster 模式

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
mindx
-
dls
namespace
:
vnpu
labels
:
ring-controller.atlas
:
ascend
-
310P
spec
:
minAvailable
:
1
schedulerName
:
volcano
policies
:
-
event
:
PodEvicted
action
:
RestartJob
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
3
queue
:
default
tasks
:
-
name
:
"default-test"
replicas
:
1
template
:
metadata
:
labels
:
app
:
infers
ring-controller.atlas
:
ascend
-
310P
vnpu-dvpp
:
"null"
vnpu-level
:
low
spec
:
schedulerName
:
volcano
containers
:
-
name
:
resnet50infer
image
:
swr.cn
-
south
-
1.myhuaweicloud.com/ascendhub/mindie
:
2.1.RC1
-
300I
-
Duo
-
py311
-
openeuler24.03
-
lts
imagePullPolicy
:
IfNotPresent
securityContext
:
privileged
:
false
command
:
[
"/bin/bash"
,
"-c"
,
"tail -f /dev/null"
]
resources
:
requests
:
huawei.com/npu-core
:
8
limits
:
huawei.com/npu-core
:
8
nodeSelector
:
host-arch
:
huawei
-
arm
```

支持的 Ascend 芯片及其
ResourceNames
如下表所示：

虚拟化任务 YAML 中 Label 说明

DVPP 与 Level 配置的影响

注意

对于
芯片虚拟化（非整卡使用）
，
vnpu-dvpp
的值必须与上表严格一致，否则任务将无法调度。

更多细节请参阅
Ascend MindCluster 文档
。

### HAMi 模式

```
apiVersion
:
v1
kind
:
Pod
metadata
:
name
:
ascend
-
pod
spec
:
schedulerName
:
volcano
containers
:
-
name
:
ubuntu
-
container
image
:
swr.cn
-
south
-
1.myhuaweicloud.com/ascendhub/ascend
-
pytorch
:
24.0.RC1
-
A2
-
1.11.0
-
ubuntu20.04
command
:
[
"sleep"
]
args
:
[
"100000"
]
resources
:
limits
:
huawei.com/Ascend310P
:
"1"
huawei.com/Ascend310P-memory
:
"4096"
```

支持的 Ascend 芯片及其
ResourceNames
如下表所示：

#### HAMi vNPU 场景下的显存分配限制

当 Pod 仅请求 1 个 vNPU 设备时，显存可配置为任意值，Job 的显存请求会自动对齐到最接近的分片策略。
示例：单卡显存为 65536，虚拟化模板为 1/4（16384）、1/2（32768）
Pod 请求 1 个 vNPU 设备且显存请求为 1024，实际分配显存为 16384
Pod 请求 1 个 vNPU 设备且显存请求为 20480，实际分配显存为 32768

当 Pod 仅请求 1 个 vNPU 设备时，显存可配置为任意值，Job 的显存请求会自动对齐到最接近的分片策略。

示例：单卡显存为 65536，虚拟化模板为 1/4（16384）、1/2（32768）
Pod 请求 1 个 vNPU 设备且显存请求为 1024，实际分配显存为 16384
Pod 请求 1 个 vNPU 设备且显存请求为 20480，实际分配显存为 32768

Pod 请求 1 个 vNPU 设备且显存请求为 1024，实际分配显存为 16384

Pod 请求 1 个 vNPU 设备且显存请求为 20480，实际分配显存为 32768

当 Pod 请求多个 vNPU 设备时，可不填写显存资源请求，或填写最大值；分配给 Pod 的显存为整卡实际显存。

---

> 完整与最新内容以官方文档为准：[Ascend vNPU 用户指南](https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_vnpu)
