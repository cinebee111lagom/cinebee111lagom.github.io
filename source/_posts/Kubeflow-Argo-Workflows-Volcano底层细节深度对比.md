---
title: Kubeflow Argo Workflows Volcano 底层细节深度对比
date: 2026-09-08 10:15:00
tags:
  - Kubeflow
  - Argo
  - Volcano
  - Kubernetes
  - AI训练
categories:
  - Kubernetes
---

---

## 1. 核心抽象

### Kubeflow：Training Job（框架级）

Kubeflow 的核心抽象围绕 **机器学习训练任务** 展开，其 CRD 层级结构如下：

```
TFJob / PyTorchJob / MPIJob / MXJob
├── ReplicaSpec (Worker)
│   ├── replicas: 3
│   ├── template: PodTemplateSpec
│   └── restartPolicy: OnFailure
├── ReplicaSpec (PS)          # TFJob 专有
│   ├── replicas: 2
│   └── ...
└── ReplicaSpec (Master)      # 可选
    └── ...
```

**底层实现要点：**

- 每种框架对应一个独立的 Operator（如 `tf-operator`、`pytorch-operator`），各自 watch 各自的 CRD
- Operator 内部维护一个 **控制循环**：`Watch CRD → Diff 期望状态与实际状态 → Create/Update/Delete Pod`
- ReplicaSpec 本质上是对 `PodTemplateSpec` 的一层包装，额外增加了 `replicas` 数量和 `restartPolicy` 语义
- Pod 的命名规则为 `{job-name}-{replica-type}-{index}`，例如 `my-tfjob-worker-0`
- 不同框架的 ReplicaSpec 语义不同：MPIJob 需要 `ssh` 注入和 `hostfile` ConfigMap；PyTorchJob 的 `MASTER_ADDR` 环境变量由 Operator 自动注入

**与底层 Pod 的关系：**

```
CRD (TFJob)
    │
    ▼  Operator 监听并翻译
Pod (worker-0)  ← 直接由 K8s 调度
Pod (worker-1)
Pod (ps-0)
```

Kubeflow **不参与调度决策**，只负责将 CRD 翻译为 Pod，调度完全交给 kube-scheduler。

---

### Argo Workflows：Workflow（DAG 编排）

Argo 的核心抽象是一个 **有向无环图（DAG）**，其 CRD 结构：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
spec:
  entrypoint: main
  templates:
    - name: main
      dag:
        tasks:
          - name: A
            template: preprocess
          - name: B
            template: train
            dependencies: [A]
            arguments:
              parameters:
                - name: data-path
                  value: "{{tasks.A.outputs.parameters.result}}"
          - name: C
            template: evaluate
            dependencies: [B]
    - name: train
      container:
        image: train:v1
      inputs:
        parameters:
          - name: data-path
      outputs:
        artifacts:
          - name: model
            path: /output/model
            s3: {...}
```

**底层实现要点：**

- **Workflow Controller** 是核心组件，以 Deployment 形式运行，watch `Workflow` CRD
- Controller 内部维护一个 **节点级状态机**，每个 DAG 节点（template）有独立状态：

```
Pending → Running → Succeeded / Failed / Error / Omitted / Skipped
```

- DAG 的执行通过 **节点评估循环** 驱动：每次循环检查所有节点的依赖是否满足，满足则创建 Pod
- **数据传递机制**：
  - `outputs.parameters`：通过文件内容提取（`valueFrom.path`），存储在 Controller 内存中
  - `outputs.artifacts`：上传到配置的 Artifact Repository（S3/GCS/OSS/MinIO），使用 `init container` 下载、`sidecar` 上传
  - 容器间不直接共享 Volume（除非显式声明 `volumeClaim`）

- **Pod 的实际形态**：
  ```
  workflow-pod (Pod)
  ├── init container: wait    ← Argo 原生等待容器，协调生命周期
  ├── init container: init    ← 下载 input artifacts（可选）
  ├── container: main         ← 用户业务容器
  └── sidecar: argoexec       ← 上传 output artifacts（可选）
  ```

- **Template 类型详解**：
  | 类型 | 行为 |
  |------|------|
  | `container` | 创建一个 Pod |
  | `script` | 内联脚本，自动包装为 `command: [bash, -c]` |
  | `dag` | 子 DAG，嵌套编排 |
  | `steps` | 顺序步骤编排（steps 内串行，steps 间可并行） |
  | `resource` | 直接 apply K8s 资源（如创建 ConfigMap） |
  | `suspend` | 人工审批/等待节点 |

---

### Volcano：Queue + PodGroup（资源调度）

Volcano 的核心抽象围绕 **批量调度**，分为两层：

**第一层：Queue（队列）**

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: team-ml
spec:
  weight: 1                    # 队列权重
  capability:                  # 队列资源上限
    cpu: "100"
    memory: "200Gi"
    nvidia.com/gpu: "16"
  reclaimable: true            # 是否可被回收
  guarantee:                   # 保障资源（最低配额）
    resource:
      cpu: "20"
      memory: "40Gi"
```

**第二层：PodGroup（调度组）**

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: PodGroup
metadata:
  name: distributed-training
spec:
  minMember: 4                 # 最少运行 Pod 数（低于此数则全部不调度）
  minResources:                # 最少需要的资源总量
    cpu: "16"
    memory: "64Gi"
    nvidia.com/gpu: "4"
  priorityClassName: high-priority
  queue: team-ml               # 所属队列
```

**底层实现要点：**

- Volcano 包含一个 **自定义 Scheduler**（`volcano-scheduler`），以 **K8s scheduler framework** 的插件形式存在，也可独立部署
- 调度流程分为三个阶段：

```
┌─────────────────────────────────────────────────┐
│              volcano-scheduler                    │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Allocate  │→│ Preempt   │→│ Enqueue/Backfill│ │
│  │ (分配)    │  │ (抢占)    │  │ (入队/回填)    │ │
│  └──────────┘  └──────────┘  └────────────────┘ │
│                                                   │
│  每个阶段由 Plugin Chain 驱动                      │
└─────────────────────────────────────────────────┘
```

- **enqueue** 阶段：判断 PodGroup 是否能进入 `Inqueue` 状态，检查 Queue 的 `capability` 和集群可用资源
- **allocate** 阶段：按 Queue 权重分配资源，同一 PodGroup 内的 Pod 要么全部分配，要么全部等待（**gang scheduling** 语义）
- **preempt** 阶段：高优先级 PodGroup 可以抢占低优先级 PodGroup 的资源，抢占粒度是 **PodGroup 级别**

---

## 2. 扩展机制

### Kubeflow：CRD + Backend Plugin

```
┌───────────────────────────────────────────────┐
│                Kubeflow 扩展层次               │
│                                                │
│  Layer 1: CRD 定义新框架                       │
│    └── 定义新的 ReplicaSpec 语义               │
│                                                │
│  Layer 2: Operator 实现                        │
│    └── 控制循环、状态聚合、环境注入             │
│                                                │
│  Layer 3: Training Operator Plugin             │
│    └── 统一的 training-operator 内部插件机制    │
│                                                │
│  Layer 4: Pipeline SDK                         │
│    └── Python DSL → Argo YAML / IR             │
└───────────────────────────────────────────────┘
```

**扩展新框架的具体步骤：**

1. 定义新的 CRD（`XxxJob`）及其 Go struct
2. 在 `training-operator` 中注册新的 Controller
3. 实现 `ReconcileXxxJob` 逻辑：Pod 创建、环境变量注入、状态计算
4. 实现 Replica 级别的状态聚合逻辑（如 AllReady、MinAvailable 等条件判断）

**Pipeline SDK 扩展：**

```python
# 自定义组件
from kfp import dsl

@dsl.component(
    base_image='my-base:latest',
    packages_to_install=['pandas', 'scikit-learn'],
)
def preprocess(data_path: str) -> Output[Dataset]:
    ...
```

SDK v2 统一使用 **IR（Intermediate Representation）YAML** 格式，后端可以对接 Argo Workflows 或 Tekton。

---

### Argo Workflows：Template + Executor + Plugin

**自定义 Executor（Container Runtime Executor）：**

Argo 支持三种 Executor 模式：

| 模式 | 原理 | 优劣 |
|------|------|------|
| `docker` | 通过 Docker socket 创建容器 | 需要挂载 docker.sock，安全性差 |
| `k8sapi` | 通过 K8s API 直接管理容器 | 不需要特权，但功能受限 |
| `emissary` | 注入 emissary 进程管理容器生命周期 | **默认模式**，安全且功能完整 |

`emissary` 的工作原理：

```
Pod
├── container: main
│   └── entrypoint 被替换为 emissary
│       ├── emissary 启动用户原始命令
│       ├── 监控进程退出码
│       └── 通过文件系统通知 Controller 状态
```

**自定义 Artifact Driver：**

```go
// 实现 ArtifactDriver 接口
type ArtifactDriver interface {
    Load(inputArtifact *v1alpha1.Artifact, path string) error
    Save(path string, outputArtifact *v1alpha1.Artifact) error
}

// 可对接：S3、GCS、OSS、Azure Blob、Git、HTTP 等
```

**Template 类型扩展（通过 Plugin 机制）：**

Argo 3.4+ 支持通过 `templateExecutor` 注册自定义的 template 类型，本质上是在 Controller 中注册新的 template 解析和执行逻辑。

---

### Volcano：Scheduler Plugin Framework

Volcano 的调度器基于 **K8s Scheduler Framework** 扩展，调度周期分为多个阶段：

```
调度一个 PodGroup 的完整周期：

1. QueueSort      ← 决定队列排序
2. PreFilter      ← 预检查资源
3. Filter         ← 过滤不满足条件的节点
4. Score          ← 对候选节点打分
5. Reserve        ← 预留资源（标记为 assumed）
6. Permit         ← 许可（gang scheduling 核心：等所有 Pod 就绪）
7. PreBind        ← 绑定前操作
8. Bind           ← 执行绑定
9. PostBind       ← 绑定后清理
```

**内置插件列表：**

| 插件 | 职责 | 实现阶段 |
|------|------|----------|
| `gang` | Gang Scheduling：PodGroup 内 Pod 全部就绪才调度 | Permit |
| `priority` | 基于优先级排序 | QueueSort |
| `proportion` | 按 Queue 权重分配资源比例 | Allocate |
| `drf` | Dominant Resource Fairness 公平调度 | Allocate |
| `nodeorder` | 节点亲和/反亲和、资源均衡 | Score |
| `binpack` | 装箱算法，提高资源利用率 | Score |
| `sla` | SLA 保障 | Allocate |
| `extender` | 外部扩展 HTTP 接口 | Filter/Score |
| `numa` | NUMA 拓扑感知调度 | Filter/Score |

**自定义插件示例：**

```go
// 实现 Plugin 接口
type MyPlugin struct {
    framework.Arguments
}

func (mp *MyPlugin) Name() string {
    return "my-custom-plugin"
}

// 在 Score 阶段注入自定义打分逻辑
func (mp *MyPlugin) Score(task *api.TaskInfo, node *v1.Node) (int, error) {
    score := 0
    // 例如：GPU 拓扑感知，优先选择 NVLink 连接的 GPU
    if hasNVLinkTopology(node) {
        score += 100
    }
    return score, nil
}

// 注册到 scheduler
func NewMyPlugin(arguments framework.Arguments) framework.Plugin {
    return &MyPlugin{Arguments: arguments}
}
```

---

## 3. 二次开发重点

### 新框架集成（Kubeflow）

以集成 **DeepSpeed Job** 为例：

```
1. 定义 CRD: DeepSpeedJob
   spec:
     launcher:        # DeepSpeed launcher 进程
       replicas: 1
       template: ...
     worker:          # 训练 worker
       replicas: 8
       template: ...
     sshPort: 22

2. Controller 核心逻辑：
   - 生成 SSH 密钥对 → 存入 Secret
   - 为每个 worker 生成 authorized_keys
   - 生成 hostfile ConfigMap（包含所有 worker 的 hostname slots）
   - 注入 DEEPSPEED_HOSTFILE、DEEPSPEED_LAUNCH 等环境变量
   - launcher Pod 依赖 worker Pod 就绪后才启动

3. 状态聚合：
   - InProgress: launcher 或 worker 正在运行
   - Succeeded: launcher 退出码为 0
   - Failed: launcher 退出码非 0
```

### 自定义 Executor（Argo）

以对接内部存储系统为例：

```go
// 实现内部 Artifacts 存储驱动
type InternalStorageDriver struct {
    Endpoint  string
    Token     string
    Namespace string
}

func (d *InternalStorageDriver) Load(artifact *wfv1.Artifact, path string) error {
    // HTTP GET from internal storage
    resp, err := http.Get(fmt.Sprintf("%s/artifacts/%s/%s",
        d.Endpoint, d.Namespace, artifact.Name))
    // 写入本地 path
    ...
}

func (d *InternalStorageDriver) Save(path string, artifact *wfv1.Artifact) error {
    // HTTP PUT to internal storage
    ...
}
```

### GPU 拓扑感知调度（Volcano）

```yaml
# 节点上部署 GPU Topology Discovery
# 自动发现 GPU 拓扑信息，写入 Node Annotation
metadata:
  annotations:
    volcano.sh/gpu-topology: |
      {
        "gpus": [
          {"id": 0, "bus": "0000:00:1e.0", "links": {"1": "NVLink", "2": "NVLink"}},
          {"id": 1, "bus": "0000:00:1e.1", "links": {"0": "NVLink", "3": "NVLink"}},
          {"id": 2, "bus": "0000:00:1f.0", "links": {"0": "NVLink", "3": "NVLink"}},
          {"id": 3, "bus": "0000:00:1f.1", "links": {"1": "NVLink", "2": "NVLink"}}
        ]
      }

# 调度器在 Score 阶段根据拓扑打分
# 优先选择 NVLink 全连接的 GPU 组
# 确保一个 Pod 的多张 GPU 在拓扑上相邻
```

---

## 4. 状态管理

### Kubeflow：Replica 级聚合

```
TFJob Status:
├── Conditions:
│   ├── Type=Created,    Status=True,  Reason=TFJobCreated
│   ├── Type=Running,    Status=True,  Reason=TFJobRunning
│   └── Type=Succeeded,  Status=True,  Reason=TFJobSucceeded
├── ReplicaStatuses:
│   ├── Active: 3    (运行中的 Pod 数)
│   ├── Succeeded: 0
│   └── Failed: 0
└── StartTime / CompletionTime
```

**状态计算逻辑（伪代码）：**

```
func calculateStatus(job):
    for each replicaType in [Worker, PS, Master]:
        active   = count(pod.phase == Running)
        succeeded = count(pod.phase == Succeeded)
        failed    = count(pod.phase == Failed)

    if failed > maxRetry:
        job.status = Failed
    elif succeeded == expectedTotal:
        job.status = Succeeded
    elif active > 0:
        job.status = Running
    else:
        job.status = Created
```

### Argo Workflows：DAG 节点级状态机

```
每个 DAG 节点（Node）的状态转换：

Pending ──→ Running ──→ Succeeded
                    ├──→ Failed
                    ├──→ Error
                    └──→ Omitted (条件跳过)

Skipped (依赖节点失败，跳过执行)

Workflow 整体状态：
  - 任一节点 Failed → Workflow Failed
  - 所有叶子节点 Succeeded → Workflow Succeeded
  - 存在 Running 节点 → Workflow Running
```

**节点状态持久化：**

```yaml
status:
  nodes:
    main-step-a:
      phase: Succeeded
      startedAt: "2024-01-01T00:00:00Z"
      finishedAt: "2024-01-01T00:05:00Z"
      outputs:
        parameters:
          - name: result
            value: "path/to/data"
        artifacts:
          - name: model
            s3:
              key: artifacts/my-workflow/model
      children:
        - main-step-b
```

状态存储在 **Workflow CRD 的 `.status.nodes` 字段**中，这是一个 map 结构，key 是节点 ID。Controller 通过比较 `spec` 与 `status.nodes` 来决定下一步操作。

### Volcano：Job/Task/PodGroup 三级状态

```
Volcano Job:
├── Job 级状态
│   ├── Pending      (等待调度)
│   ├── Aborting     (正在中止)
│   ├── Aborted      (已中止)
│   ├── Running      (运行中)
│   ├── Restarting   (正在重启)
│   ├── Completed    (已完成)
│   └── Terminate    (终止)
│
├── Task 级状态
│   ├── Task 状态独立计算
│   └── 每个 Task 有自己的 replicas / succeeded / failed 计数
│
└── PodGroup 级状态（由 scheduler 维护）
    ├── Pending      (未入队)
    ├── Inqueue      (已入队，等待资源)
    ├── Running      (已分配资源)
    └── Completed    (完成)
```

**三级状态联动：**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Job 控制器  │◄──│  Task 状态   │◄──│  Pod 状态    │
│  (vk-ctl)    │    │  (聚合)      │    │  (K8s)      │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       ▼                  ▼                  ▼
  更新 Job Status    统计 succeeded/    Pod 实际的
  Condition          failed/running     Phase
```

**PodGroup 与 Job 的关联：**

Volcano Job Controller 在创建 Job 时，会自动创建对应的 PodGroup。PodGroup 的 `minMember` 和 `minResources` 由 Job 的 Task 定义计算得出。Scheduler 根据 PodGroup 的状态决定是否将 Pod 放行。

---

## 5. 与 K8s 集成深度

### Kubeflow（中等）

```
K8s API Server
    │
    ├── kube-scheduler ← 标准调度，Kubeflow 不干预
    │
    ├── tf-operator    ← Watch TFJob CRD → Create Pod
    │                     不参与调度，只管理生命周期
    │
    └── kubeflow-pipelines ← Watch Workflow → Create Argo Workflow
                              间接编排
```

Kubeflow 的集成点仅在 **API 层**（CRD 定义和 Controller 逻辑），不触碰调度层。Pod 的调度策略通过标准的 `nodeSelector`、`affinity`、`tolerations` 等字段传递。

### Argo Workflows（中等）

```
K8s API Server
    │
    ├── kube-scheduler ← 标准调度
    │
    └── workflow-controller
        ├── Watch Workflow CRD
        ├── Create Pod（注入 wait/init/sidecar 容器）
        ├── Watch Pod 状态变化
        ├── 管理 PVC（动态创建/删除）
        └── 管理 ConfigMap（存储中间参数）
```

Argo 深入使用了 PVC 进行数据缓存（`volumes` + `volumeClaimTemplates`），但调度本身仍由 kube-scheduler 负责。

### Volcano（深度集成）

```
K8s API Server
    │
    └── volcano-scheduler（作为 Scheduling Framework 插件）
        ├── QueueSort Plugin   ← 队列排序
        ├── Allocate Plugin    ← 资源分配（抢占 kube-scheduler 的决策权）
        ├── Gang Plugin        ← Gang Scheduling（不允许单独调度）
        ├── DRF Plugin         ← 公平调度算法
        ├── Binpack Plugin     ← 装箱优化
        └── NUMA Plugin        ← 拓扑感知
```

Volcano **直接扩展了调度层**，而不是在调度之上做封装。它本质上是一个 **增强版的 kube-scheduler**，替代或补充默认调度器的决策。这意味着：

- 可以实现 `kube-scheduler` 不支持的 gang scheduling 语义
- 可以在调度层面实现队列间的资源隔离和公平分配
- 可以在 `Filter` 和 `Score` 阶段注入自定义的 GPU 拓扑感知逻辑

---

## 6. 适用场景

### Kubeflow

```
典型部署架构：

┌─────────────────────────────────────────────────┐
│                 Kubeflow Platform                │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │
│  │ Katib    │  │ KFServing│  │  Pipelines    │ │
│  │ (超参搜索)│  │ (模型服务)│  │  (工作流编排) │ │
│  └──────────┘  └──────────┘  └───────────────┘ │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │
│  │ TFJob    │  │PyTorchJob│  │  Notebook     │ │
│  │ Operator │  │ Operator │  │  Server       │ │
│  └──────────┘  └──────────┘  └───────────────┘ │
│                                                  │
│  适用：端到端 ML 平台，训练+服务+实验管理        │
└─────────────────────────────────────────────────┘
```

适合需要 **完整 ML 生命周期管理** 的团队：数据预处理 → 训练 → 超参搜索 → 模型注册 → 在线/离线推理。

### Argo Workflows

```
典型使用模式：

1. CI/CD 流水线
   Build → Test → Deploy → Smoke Test

2. 数据处理 Pipeline
   Extract → Transform → Validate → Load

3. 通用批处理
   多步骤、有依赖关系的任意任务编排

优势：通用性强，不限于 ML 场景
劣势：不理解 ML 训练语义（没有 gang scheduling、
      没有框架级环境注入）
```

### Volcano

```
典型使用模式：

1. 大规模分布式训练调度
   └── 配合 Kubeflow 使用，替代 default-scheduler

2. HPC 批处理作业
   └── 队列管理 + 资源配额 + 优先级调度

3. 混合负载
   └── 在线推理（低延迟）+ 离线训练（高吞吐）共享集群
   └── 通过 Queue 实现资源隔离

架构位置：
  ┌─────────────────────────────────────┐
  │         Kubeflow / 自研平台          │
  │     (定义训练任务，管理生命周期)      │
  └─────────────┬───────────────────────┘
                │ 创建 Pod
                ▼
  ┌─────────────────────────────────────┐
  │         Volcano Scheduler            │
  │     (决定 Pod 放在哪个节点)           │
  │     (gang scheduling + 队列管理)      │
  └─────────────┬───────────────────────┘
                │ 绑定 Pod
                ▼
  ┌─────────────────────────────────────┐
  │         K8s Nodes                    │
  └─────────────────────────────────────┘
```

---

## 总结：三者关系

```
不是竞争关系，而是分层互补：

┌───────────────────────────────┐
│     编排层 (Orchestration)      │  Kubeflow Pipelines / Argo
│     "做什么任务，按什么顺序"     │
├───────────────────────────────┤
│     框架层 (Framework)          │  Kubeflow Operators (TF/PyTorch/...)
│     "如何运行特定框架的训练"     │
├───────────────────────────────┤
│     调度层 (Scheduling)         │  Volcano / kube-scheduler
│     "Pod 放在哪里，资源怎么分"   │
├───────────────────────────────┤
│     基础设施层 (Infra)          │  Kubernetes
└───────────────────────────────┘

实际生产中常见组合：
  Argo Workflows + Volcano     → 通用 DAG 编排 + 高级调度
  Kubeflow + Volcano           → ML 全生命周期 + Gang Scheduling
  Argo + Kubeflow Operators    → Pipeline 编排 + 框架级训练管理
```
