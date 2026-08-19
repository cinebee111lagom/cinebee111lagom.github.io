---
title: Kubernetes 相关机制详解
date: 2026-09-08 08:00:00
tags:
  - Kubernetes
  - 调度器
  - HPA
  - DaemonSet
categories:
  - Kubernetes
---

## 1. Scheduler（调度器）

### 默认调度器的工作逻辑

```
Pod 请求资源
    │
    ▼
┌─────────────┐
│  Filtering   │  ← 过滤不满足条件的节点（资源不足、污点等）
└──────┬──────┘
       ▼
┌─────────────┐
│   Scoring    │  ← 对候选节点打分（资源均衡、亲和性等）
└──────┬──────┘
       ▼
  选择最高分节点绑定 Pod
```

### 默认调度器的局限

| 能力 | 默认 kube-scheduler | 说明 |
|------|-------------------|------|
| CPU/内存调度 | 支持 | `requests` / `limits` |
| GPU 调度 | 部分支持 | 仅 `nvidia.com/gpu` 资源计数，不做拓扑感知 |
| Gang Scheduling | 不支持 | 无法保证一组 Pod 同时调度 |
| 优先级抢占 | 支持 | `PriorityClass` 机制 |
| 拓扑感知 | 有限 | 不理解 NVLink/NVSwitch 互联拓扑 |

### GPU 调度的痛点与解决方案

```
场景：训练任务需要 8 张 GPU，必须在同一台机器上

默认调度器的问题：
  Pod A → 分到 node-1 的 GPU 0-3
  Pod B → 分到 node-2 的 GPU 0-3  ← 跨节点，NCCL 通信走网络，性能骤降

解决方案层次：
┌──────────────────────────────────────────────┐
│  Device Plugin（Kubernetes 原生）              │
│  → 暴露 GPU 为扩展资源                         │
│  → 但不感知拓扑                                │
├──────────────────────────────────────────────┤
│  Topology Manager（Kubernetes 1.18+）         │
│  → NUMA 拓扑感知，保证 CPU/GPU 同 NUMA        │
│  → 但不处理跨节点 Gang                         │
├──────────────────────────────────────────────┤
│  Volcano / Coscheduling（调度器插件）          │
│  → Gang Scheduling：一组 Pod 要么全部调度      │
│    要么全部等待，避免死锁                       │
│  → 队列管理、公平调度、抢占                     │
├──────────────────────────────────────────────┤
│  HAMI / GPU-Share（Device Plugin 扩展）        │
│  → GPU 共享（vGPU）、显存隔离                  │
│  → 单卡切分给多个小任务                        │
└──────────────────────────────────────────────┘
```

### Volcano Gang Scheduling 核心流程

```
用户提交 PodGroup (minMember=8)
         │
         ▼
    Volcano Scheduler
         │
         ├── 1. 检查是否有 ≥8 个节点资源同时可用
         │
         ├── 2. 如果不满足 → PodGroup Pending（全部等待）
         │
         └── 3. 如果满足 → 一次性绑定 8 个 Pod
                          到满足条件的节点
                          
效果：避免 "部分 Pod 启动后占着资源等其他 Pod" 的死锁
```

---

## 2. Controller Manager（控制器管理器）

### 控制循环（Reconciliation Loop）核心原理

```
┌─────────────────────────────────────────────┐
│              控制循环（通用模式）               │
│                                             │
│   ① Observe  → 观测当前实际状态（Actual）     │
│   ② Diff     → 与期望状态（Desired）比较      │
│   ③ Act      → 执行动作使 Actual → Desired   │
│                                             │
│   循环往复，最终收敛                           │
└─────────────────────────────────────────────┘
```

### 三种核心控制器对比

```
┌─────────────────────────────────────────────────────────┐
│                    Deployment Controller                  │
├─────────────────────────────────────────────────────────┤
│  期望状态：replicas=3, image=nginx:v2                    │
│                                                         │
│  控制逻辑：                                              │
│  ┌──────────────┐    滚动更新策略                         │
│  │ ReplicaSet v2 │ ←── 新建                              │
│  │  Pod Pod Pod  │    逐步扩容                            │
│  └──────────────┘                                       │
│  ┌──────────────┐                                       │
│  │ ReplicaSet v1 │ ←── 逐步缩容到 0                      │
│  │  (empty)      │                                       │
│  └──────────────┘                                       │
│                                                         │
│  适用：无状态服务（Web、API）                              │
│  特点：Pod 可任意替换，无固定身份                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    StatefulSet Controller                 │
├─────────────────────────────────────────────────────────┤
│  期望状态：replicas=3, 有序部署                           │
│                                                         │
│  控制逻辑：                                              │
│  pod-0  ──创建并Ready──→  pod-1  ──Ready──→  pod-2       │
│  (有序，前一个就绪才创建下一个)                            │
│                                                         │
│  特点：                                                  │
│  • 稳定的网络标识：pod-0.svc, pod-1.svc                  │
│  • 稳定的持久存储：PVC 与 Pod 名称绑定                     │
│  • 有序部署/扩缩容/删除                                   │
│                                                         │
│  适用：有状态服务（数据库、分布式存储、MQ）                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      Job Controller                      │
├─────────────────────────────────────────────────────────┤
│  期望状态：completions=5, parallelism=2                  │
│                                                         │
│  控制逻辑：                                              │
│  ┌─────┐ ┌─────┐                                       │
│  │Pod-1│ │Pod-2│  ← 并行运行 2 个                       │
│  │ ✅  │ │ ✅  │  ← 完成后计数 +2                        │
│  └─────┘ └─────┘                                       │
│  ┌─────┐ ┌─────┐                                       │
│  │Pod-3│ │Pod-4│  ← 再启动 2 个                         │
│  │ ✅  │ │ ✅  │  ← 完成后计数 +2                        │
│  └─────┘ └─────┘                                       │
│  ┌─────┐                                               │
│  │Pod-5│  ← 最后 1 个                                   │
│  │ ✅  │  ← completions=5 达成，Job 完成                 │
│  └─────┘                                               │
│                                                         │
│  适用：批处理、一次性任务                                  │
└─────────────────────────────────────────────────────────┘
```

### 与 ML 训练场景的映射

| 场景 | 控制器选择 | 原因 |
|------|-----------|------|
| 模型推理服务 | Deployment | 无状态，可水平扩展 |
| 分布式训练（PS 模式） | Job / TFJob | 训练完成即退出 |
| 分布式训练（AllReduce） | Job + Gang Scheduling | 需要多 Worker 同时启动 |
| Jupyter Notebook | StatefulSet | 需要持久化用户环境 |
| 特征存储 | StatefulSet | 有状态，数据持久化 |

---

## 3. CRD（Custom Resource Definition）

### CRD 的扩展机制

```
标准 Kubernetes 资源：
  Pod, Service, Deployment, ConfigMap ...

扩展资源（通过 CRD 定义）：
  TFJob, PyTorchJob, MPIJob, JupyterNotebook ...

工作原理：
┌──────────────────────────────────────────┐
│            Kubernetes API Server          │
│                                          │
│  /api/v1/pods              ← 原生资源     │
│  /apis/apps/v1/deployments ← 原生资源     │
│                                          │
│  /apis/kubeflow.org/v1/                  │
│      pytorchjobs          ← CRD 扩展资源  │
│      tfjobs               ← CRD 扩展资源  │
│      notebooks            ← CRD 扩展资源  │
└────────────────┬─────────────────────────┘
                 │ Watch 变更
                 ▼
┌──────────────────────────────────────────┐
│         自定义 Controller（Operator）       │
│                                          │
│  PyTorchJob Operator:                    │
│  ① 创建 Master Pod                       │
│  ② 创建 Worker Pods（Gang Scheduling）    │
│  ③ 监控训练进度，更新 Job 状态             │
│  ④ 处理失败重启                           │
└──────────────────────────────────────────┘
```

### Kubeflow CRD 实例：PyTorchJob

```yaml
# 用户提交的 PyTorchJob YAML
apiVersion: "kubeflow.org/v1"
kind: PyTorchJob
metadata:
  name: mnist-training
spec:
  pytorchReplicaSpecs:
    Master:                    # Master 角色
      replicas: 1
      template:
        spec:
          containers:
            - name: pytorch
              image: pytorch-example:latest
              resources:
                limits:
                  nvidia.com/gpu: 1
    Worker:                    # Worker 角色
      replicas: 4
      template:
        spec:
          containers:
            - name: pytorch
              image: pytorch-example:latest
              resources:
                limits:
                  nvidia.com/gpu: 2    # 每个 Worker 2 张 GPU
```

```
PyTorchJob Controller 内部逻辑：

Watch 到 PyTorchJob 创建事件
        │
        ▼
  创建 1 个 Master Pod (1 GPU)
        │
        ▼
  创建 4 个 Worker Pod (各 2 GPU)  ← 共 9 张 GPU
        │
        ▼
  注入环境变量：
    MASTER_ADDR=master-0 的 Pod IP
    MASTER_PORT=23456
    WORLD_SIZE=5
    RANK=0 (master), 1~4 (workers)
        │
        ▼
  监控所有 Pod 状态 → 更新 PyTorchJob status
        │
        ├── 全部 Succeeded → Job 状态 = Succeeded
        ├── 任一 Failed    → 根据 restartPolicy 决定
        └── 运行中         → 继续监控
```

### CRD + Controller 的完整生态

```
┌─────────────────────────────────────────────────────┐
│                  Kubernetes 原生层                     │
│  Pod, Service, ConfigMap, PVC, Node ...             │
├─────────────────────────────────────────────────────┤
│                  CRD 扩展层                           │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Kubeflow  │  │ Volcano  │  │ Kueue    │          │
│  │          │  │          │  │          │          │
│  │ TFJob    │  │ Queue    │  │ Job      │          │
│  │ PyTorch  │  │ PodGroup │  │ Queue    │          │
│  │ MPIJob   │  │ VCJob    │  │ Workload │          │
│  │ Notebook │  │          │  │          │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Istio    │  │ Knative  │  │ Argo     │          │
│  │          │  │          │  │          │          │
│  │ Virtual  │  │ Service  │  │ Workflow │          │
│  │ Service  │  │ Revision │  │ Step     │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
```

---

## 三者的协作关系

```
一次完整 ML 训练任务的生命周期：

① 用户提交 PyTorchJob (CRD 资源)
         │
         ▼
② PyTorchJob Controller 感知到新资源
   计算需要 1 Master + 4 Worker = 5 个 Pod
         │
         ▼
③ Controller 向 API Server 创建 5 个 Pod 对象
   （此时 Pod 处于 Pending，尚未调度）
         │
         ▼
④ Volcano Scheduler（替代默认调度器）介入
   检查 Gang 条件：是否有 9 张 GPU 可同时分配
         │
         ├── 资源不足 → PodGroup Pending，等待
         │
         └── 资源充足 → 一次性将 5 个 Pod 绑定到节点
         │
         ▼
⑤ kubelet 在各节点启动容器
   nvidia-device-plugin 挂载 GPU
         │
         ▼
⑥ Controller 持续监控
   更新 PyTorchJob status 字段
   处理失败重启 / 完成清理
```

这套架构的核心思想是：**Kubernetes 提供通用的声明式 API + 控制循环框架，ML 特有的复杂性通过 CRD + 自定义 Controller + 调度器插件逐层封装**，每一层都可以独立演进和替换。
