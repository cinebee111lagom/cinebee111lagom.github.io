---
title: Kubeflow Argo Volcano 二次开发底层设计
date: 2026-09-08 10:00:00
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

## 一、总体架构定位



三者在 Kubernetes 生态中各司其职，理解它们的定位是二次开发的前提：

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI/ML 平台层                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Kubeflow                                 │  │
│  │  Pipeline · Training Operator · KServe · Notebook          │  │
│  └──────────────┬──────────────────────┬─────────────────────┘  │
│                 │                      │                         │
│  ┌──────────────▼──────────┐ ┌────────▼────────────────────┐   │
│  │       Argo Workflows    │ │        Volcano               │   │
│  │  DAG编排·CI/CD·ETL     │ │  Gang Scheduling·Queue·GPU   │   │
│  └──────────────┬──────────┘ └────────┬────────────────────┘   │
│                 │                      │                         │
│  ┌──────────────▼──────────────────────▼─────────────────────┐  │
│  │                   Kubernetes API Server                    │  │
│  │          CRD · Controller · Scheduler · Admission          │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```



---

## 二、Kubernetes 扩展模型基础（三者共同底层）

### 2.1 Operator 模式

三个项目都遵循 Kubernetes **Operator 模式**——通过 CRD 声明期望状态，通过 Controller 不断驱动实际状态向期望状态收敛：

```go
// 核心控制循环伪代码
func (c *Controller) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    // 1. 获取 CR (Custom Resource) 当前状态
    obj := &v1.MyCustomResource{}
    if err := c.Get(ctx, req.NamespacedName, obj); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }

    // 2. 对比期望状态 vs 实际状态
    desired := obj.Spec   // 用户声明
    actual := c.observe(ctx, obj) // 从集群观察

    // 3. 执行调谐（Reconcile）：驱动 actual → desired
    if !reflect.DeepEqual(desired, actual) {
        if err := c.actuate(ctx, obj, desired, actual); err != nil {
            return ctrl.Result{}, err
        }
    }

    // 4. 更新 Status 子资源
    obj.Status.Phase = "Running"
    c.Status().Update(ctx, obj)

    return ctrl.Result{}, nil
}
```

### 2.2 CRD 设计范式

```
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: myresources.example.com
spec:
  group: example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:        # 期望状态（用户写）
              type: object
            status:      # 实际状态（Controller 写）
              type: object
      subresources:
        status: {}       # 启用 /status 子资源
      additionalPrinterColumns:
        - name: Phase
          type: string
          jsonPath: .status.phase
  names:
    kind: MyResource
    plural: myresources
  scope: Namespaced
```

### 2.3 Informer 机制（三者共同依赖）



```
┌──────────┐   Watch    ┌─────────────┐   Add/Update/Delete   ┌──────────┐
│ API      │ ──────────▶│  Reflector  │ ─────────────────────▶│ Delta    │
│ Server   │            │             │                        │ FIFO    │
└──────────┘            └─────────────┘                        └────┬─────┘
                                                                    │ Pop
                                                               ┌────▼─────┐
                                                               │ Informer │
                                                               │(Handler) │
                                                               └────┬─────┘
                                                     ┌──────────────┼──────────────┐
                                               ┌─────▼────┐   ┌─────▼────┐   ┌─────▼────┐
                                               │AddFunc    │   │UpdateFunc│   │DeleteFunc│
                                               └─────┬────┘   └─────┬────┘   └─────┬────┘
                                                     └──────────────┼──────────────┘
                                                               ┌────▼─────┐
                                                               │WorkQueue │
                                                               │(限速队列) │
                                                               └────┬─────┘
                                                               ┌────▼─────┐
                                                               │Controller│
                                                               │ Worker   │
                                                               └──────────┘
```

---

## 三、Kubeflow 二次开发底层设计

### 3.1 核心组件架构

```
┌──────────────────────────────────────────────────────────────┐
│                        Kubeflow Platform                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Pipelines   │  │   Training   │  │     KServe        │  │
│  │  (KFP SDK    │  │   Operators  │  │  (Model Serving)  │  │
│  │   + Argo)    │  │              │  │                   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                 │                    │             │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌────────▼──────────┐  │
│  │ API Server   │  │  TFJob/      │  │  InferenceService │  │
│  │ + DB + Store │  │  PyTorchJob/ │  │  Controller       │  │
│  └──────────────┘  │  MPIJob/...  │  └───────────────────┘  │
│                    │  Controller  │                          │
│                    └──────────────┘                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │  Notebook    │  │  Katib       │                         │
│  │  Controller  │  │  (HPO)       │                         │
│  └──────────────┘  └──────────────┘                         │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Training Operator 底层设计

#### CRD 继承体系

```go
// 以 PyTorchJob 为例，核心类型定义
type PyTorchJob struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`
    Spec              PyTorchJobSpec   `json:"spec,omitempty"`
    Status            JobStatus        `json:"status,omitempty"`
}

type PyTorchJobSpec struct {
    // 基于 kubernetes.io 的 PodTemplateSpec
    PyTorchReplicaSpecs map[ReplicaType]*ReplicaSpec `json:"pytorchReplicaSpecs"`
    // 例如: {"Master": ..., "Worker": ...}
}

type ReplicaSpec struct {
    Replicas      *int32                  `json:"replicas"`
    Template      corev1.PodTemplateSpec  `json:"template"`
    RestartPolicy RestartPolicy           `json:"restartPolicy"`
}
```

#### Controller 调谐逻辑

```
PyTorchJob CR 创建
       │
       ▼
┌──────────────┐
│  Reconcile   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐    否    ┌─────────────────┐
│ Job 已存在？     │────────▶│ 创建 Pod/Service│
└──────┬───────────┘         └─────────────────┘
       │ 是
       ▼
┌──────────────────┐    是    ┌─────────────────┐
│ 所有 Replica     │────────▶│ Phase=Running   │
│ Ready?           │         └─────────────────┘
└──────┬───────────┘
       │ 否
       ▼
┌──────────────────┐    失败   ┌─────────────────┐
│ Master 失败？    │─────────▶│ Phase=Failed    │
│                  │          │ 清理资源         │
└──────┬───────────┘          └─────────────────┘
       │
       ▼
┌──────────────────┐
│ 等待重新调谐     │
└──────────────────┘
```

#### 二次开发切入点

```go
// 1. 自定义新的 Training Job 类型
// 继承 common 框架，只需实现 ReplicaType 枚举

type ReplicaType string
const (
    ReplicaTypeMaster ReplicaType = "Master"
    ReplicaTypeWorker ReplicaType = "Worker"
    ReplicaTypePS     ReplicaType = "PS"
    ReplicaTypeChief  ReplicaType = "Chief"
    // 二次开发扩展点：添加自定义角色
    ReplicaTypeEvaluator ReplicaType = "Evaluator"
)

// 2. 自定义调度策略（与 Volcano 联动）
// 在 PodTemplate 中注入 volcano.sh/queue 等 annotation
spec:
  pytorchReplicaSpecs:
    Worker:
      template:
        metadata:
          annotations:
            volcano.sh/queue: "ml-training"
            volcano.sh/gang-scheduling: "true"
```

### 3.3 Kubeflow Pipeline 底层设计

#### 编译流程

```
Python SDK (KFP v2)
       │
       ▼
┌──────────────────┐
│ @dsl.component   │   定义一个组件（函数 → 容器）
│ @dsl.pipeline    │   定义 DAG 拓扑
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Compiler         │   IR YAML 编译
│ .compile()       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ PipelineSpec     │   中间表示 (IR)
│ (protobuf)       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ API Server       │   存储 + 调度
│ → Argo Workflow  │   生成底层执行 DAG
└──────────────────┘
```

#### IR YAML 结构

```yaml
# pipeline.yaml (编译产物)
pipelineInfo:
  name: my-training-pipeline
root:
  dag:
    tasks:
      preprocess:
        componentRef:
          name: comp-preprocess
        inputs:
          parameters:
            input_path:
              runtimeValue:
                runtimeParameter: input_path
        dependentTasks: []
      train:
        componentRef:
          name: comp-train
        dependentTasks:
          - preprocess
      evaluate:
        componentRef:
          name: comp-evaluate
        dependentTasks:
          - train
components:
  comp-preprocess:
    executorLabel: exec-preprocess
  comp-train:
    executorLabel: exec-train
deploymentSpec:
  executors:
    exec-preprocess:
      container:
        image: my-registry/preprocess:v1
        command: [python, /pipelines/component/src/preprocess.py]
```

#### 二次开发：自定义 Backend Plugin

```go
// Kubeflow Pipeline v2 支持 Backend Plugin 机制
// 实现以下 gRPC 接口:

type BackendPluginServer interface {
    // 调度阶段 Hook
    HandleSubmitJob(ctx, *SubmitJobRequest) (*SubmitJobResponse, error)
    // 状态同步 Hook
    HandleGetJob(ctx, *GetJobRequest) (*GetJobResponse, error)
    // 取消任务 Hook
    HandleTerminateJob(ctx, *TerminateJobRequest) (*TerminateJobResponse, error)
}

// 注册示例（gRPC）
func main() {
    listener, _ := net.Listen("tcp", ":8080")
    grpcServer := grpc.NewServer()
    pipelines.RegisterBackendPluginServer(grpcServer, &MyPlugin{})
    grpcServer.Serve(listener)
}
```

---

## 四、Argo Workflows 二次开发底层设计

### 4.1 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                   Argo Workflows                         │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Workflow     │  │  CronWorkflow│  │  Workflow     │  │
│  │  Controller   │  │  Controller  │  │  Template     │  │
│  └──────┬───────┘  └──────┬───────┘  │  Resolver     │  │
│         │                 │          └──────┬───────┘  │
│         └────────────┬────┘                 │          │
│              ┌───────▼───────┐              │          │
│              │   Main        │◀─────────────┘          │
│              │   Controller  │                          │
│              └───────┬───────┘                          │
│                      │                                  │
│  ┌───────────────────▼────────────────────────────┐    │
│  │           Execution Engine                       │    │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │    │
│  │  │DAG Engine│ │Step Engine│ │ Container Set  │  │    │
│  │  └──────────┘ └──────────┘ └────────────────┘  │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  Artifact     │  │  Executor    │                    │
│  │  Repository   │  │  (Emissary)  │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Workflow CRD 核心数据模型

```go
type Workflow struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`
    Spec              WorkflowSpec   `json:"spec"`
    Status            WorkflowStatus `json:"status"`
}

type WorkflowSpec struct {
    Templates      []Template          `json:"templates"`
    Entrypoint     string              `json:"entrypoint"`      // 入口模板名
    Arguments      Arguments           `json:"arguments,omitempty"`
    VolumeClaimTemplates []corev1.PersistentVolumeClaim `json:"volumeClaimTemplates,omitempty"`
    PodMetadata    *Metadata           `json:"podMetadata,omitempty"`
    Hooks          LifecycleHooks      `json:"hooks,omitempty"`  // 生命周期钩子
}

type Template struct {
    Name      string            `json:"name"`
    // 模板类型（互斥）
    *PodSpec                   // Inline Pod spec
    *DAGTemplate              // DAG 编排
    *Steps                    // 顺序/并行步骤编排
    *ContainerSetTemplate     // 同 Pod 多容器
    *Script                   // 内联脚本

    Inputs      Inputs          `json:"inputs,omitempty"`
    Outputs     Outputs         `json:"outputs,omitempty"`
    RetryStrategy *RetryStrategy `json:"retryStrategy,omitempty"`
    Affinity    *corev1.Affinity `json:"affinity,omitempty"`
    Metadata    Metadata        `json:"metadata,omitempty"`
    NodeSelector map[string]string `json:"nodeSelector,omitempty"`
}
```

### 4.3 Controller 调谐核心流程

```
┌──────────────────────────────────────────────────────────────┐
│              Workflow Reconcile Loop                          │
│                                                              │
│  1. 读取 Workflow Spec                                       │
│     │                                                        │
│  2. 构建 Execution Graph (DAG / Steps)                       │
│     │                                                        │
│  3. 遍历节点状态:                                            │
│     │                                                        │
│     ├── Pending  → 检查依赖是否满足 → 创建 Pod              │
│     ├── Running  → Watch Pod Status → 更新节点状态           │
│     ├── Succeeded→ 通知下游节点解除阻塞                      │
│     ├── Failed   → 执行 RetryStrategy 或标记失败            │
│     └── Omitted  → 跳过（When 条件为 false）                │
│     │                                                        │
│  4. 聚合状态 → 更新 Workflow.Status.Phase                    │
│     │                                                        │
│  5. 处理 Artifacts (归档/传递)                                │
│     │                                                        │
│  6. 处理 Hooks (lifecycle events)                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.4 二次开发切入点

#### A. 自定义 Executor（执行器）

```go
// Argo 的 Emissary Executor 通过 PID 1 代理容器生命周期
// 二次开发可以替换为自定义 executor

// workflow-controller-configmap
executor: |
  image: my-registry/custom-executor:v1
  command:
    - /var/run/argo/argoexec
  resources:
    requests:
      cpu: 100m
      memory: 64Mi

// 自定义 Executor 需实现:
// 1. Init 阶段：准备输入 artifacts
// 2. Wait 阶段：监控容器退出码 + 收集输出
// 3. Kill 阶段：优雅终止
```

#### B. 自定义 Template Types（通过 Plugin）

```go
// Argo 支持通过 HTTP/gRPC 调用外部 Plugin
// 扩展自定义节点类型

type ExecutorPlugin interface {
    // 执行自定义逻辑
    Execute(args ExecuteTemplateArgs) (*ExecuteTemplateResult, error)
}

// Workflow 中引用：
// template:
//   plugin:
//     myCustomPlugin:
//       param1: "value1"
```

#### C. 自定义 Artifact Repository

```go
// 实现 ArtifactDriver 接口
type ArtifactDriver interface {
    Load(inputArtifact *Artifact, path string) error
    Save(path string, outputArtifact *Artifact) error
    ListObjects(artifact *Artifact) ([]string, error)
    // 二次开发: 添加自定义存储后端
    // 例如: HDFS, Ceph, 自研对象存储
}

// 注册示例
func init() {
    drivers["myoss"] = &MyOSSDriver{
        Endpoint: os.Getenv("OSS_ENDPOINT"),
        Bucket:   os.Getenv("OSS_BUCKET"),
    }
}
```

#### D. Workflow Template + ClusterWorkflowTemplate 复用

```yaml
# 二次开发中，将通用 Pipeline 抽象为可复用模板
apiVersion: argoproj.io/v1alpha1
kind: ClusterWorkflowTemplate
metadata:
  name: distributed-training
spec:
  templates:
    - name: train-main
      inputs:
        parameters:
          - name: image
          - name: epochs
          - name: lr
      container:
        image: "{{inputs.parameters.image}}"
        command: [python, train.py]
        args:
          - "--epochs={{inputs.parameters.epochs}}"
          - "--lr={{inputs.parameters.lr}}"
        resources:
          requests:
            nvidia.com/gpu: "1"

    - name: train-worker
      # ...类似结构

  entrypoint: distributed-dag
  # ...DAG 定义
```

---

## 五、Volcano 二次开发底层设计

### 5.1 核心架构

```
┌──────────────────────────────────────────────────────────────────┐
│                         Volcano                                    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                    Scheduling Layer                           ││
│  │                                                              ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  ││
│  │  │  Gang    │ │  Fair    │ │  DRF     │ │  Topology     │  ││
│  │  │  Scheduler│ │  Share   │ │          │ │  Aware        │  ││
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  ││
│  │                                                              ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                    ││
│  │  │  Binpack │ │  SLA     │ │  Preempt │                    ││
│  │  │          │ │          │ │          │                    ││
│  │  └──────────┘ └──────────┘ └──────────┘                    ││
│  │                                                              ││
│  │  Plugin Framework:                                           ││
│  │  ┌────────────────────────────────────────────────────────┐ ││
│  │  │ Enqueue  → Allocate  → Preempt  → Reclaim  → Backfill │ ││
│  │  │ (入队)    (分配)      (抢占)     (回收)     (回填)     │ ││
│  │  └────────────────────────────────────────────────────────┘ ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                    Control Layer                              ││
│  │                                                              ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                  ││
│  │  │ Queue    │  │ Job      │  │ Command  │                  ││
│  │  │ Controller│  │ Controller│  │ Controller│                  ││
│  │  └──────────┘  └──────────┘  └──────────┘                  ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  CRDs:                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        ││
│  │  Queue   │  │  Job     │  │ PodGroup │  │ Command  │        ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        ││
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 核心 CRD 数据模型

#### Queue（队列）

```go
type Queue struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`
    Spec              QueueSpec   `json:"spec,omitempty"`
    Status            QueueStatus `json:"status,omitempty"`
}

type QueueSpec struct {
    // 权重：用于 Fair Share 计算
    Weight     int32 `json:"weight"`
    // 能力（资源上限）
    Capability v1.ResourceList `json:"capability,omitempty"`
    // 国家/组织等扩展维度
    ExtendClusterClis map[string]intstr.IntOrString `json:"extendClusterClis,omitempty"`
    // 层级队列
    Parent     string `json:"parent,omitempty"`
    // 重新声明策略
    Reclaimable *bool `json:"reclaimable,omitempty"`
}
```

#### Job（Volcano Job，区别于 Kubernetes batch Job）

```go
type Job struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`
    Spec              JobSpec   `json:"spec,omitempty"`
    Status            JobStatus `json:"status,omitempty"`
}

type JobSpec struct {
    MinAvailable  *int32                `json:"minAvailable"`   // Gang Scheduling 最小可用数
    SchedulerName string                `json:"schedulerName"`  // "volcano"
    Queue         string                `json:"queue"`
    Policies      []LifecyclePolicy     `json:"policies"`       // 重启/退出策略
    Plugins       map[string][]string   `json:"plugins"`        // 启用的插件
    MaxRetry      int32                 `json:"maxRetry"`
    Tasks         []TaskSpec            `json:"tasks"`          // 多角色任务
    // Tensorflow/PyTorch 等框架集成
    RunningEstimate *Duration           `json:"runningEstimate,omitempty"`
}

type TaskSpec struct {
    Name      string                  `json:"name"`
    Replicas  int32                   `json:"replicas"`
    Template  corev1.PodTemplateSpec `json:"template"`
    Policies  []LifecyclePolicy      `json:"policies"`
    // 优先级（用于差异化调度）
    Priority  *string                `json:"priority,omitempty"`
}
```

#### PodGroup（Gang Scheduling 核心）

```go
type PodGroup struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`
    Spec              PodGroupSpec   `json:"spec,omitempty"`
    Status            PodGroupStatus `json:"status,omitempty"`
}

type PodGroupSpec struct {
    MinMember    *int32          `json:"minMember"`     // 最少 Pod 数
    MinResources *v1.ResourceList `json:"minResources"`  // 最少资源需求
    Queue        string          `json:"queue"`
    PriorityClassName string    `json:"priorityClassName"`
}
```

### 5.3 调度框架 Plugin 机制（深度二次开发核心）



Volcano 的调度器基于 **插件化框架**，每个调度阶段都可以插入自定义逻辑：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Volcano Scheduler Framework                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Session (一次调度周期)                 │    │
│  │                                                          │    │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐           │    │
│  │  │ Open()   │───▶│ Execute  │───▶│ Close()  │           │    │
│  │  │ 初始化   │    │ 核心逻辑 │    │ 清理     │           │    │
│  │  └──────────┘    └──────────┘    └──────────┘           │    │
│  │                                                          │    │
│  │  Execute 阶段:                                           │    │
│  │                                                          │    │
│  │  ┌────────────────────────────────────────────────────┐ │    │
│  │  │                                                    │ │    │
│  │  │  ┌──────┐  ┌──────────┐  ┌────────┐  ┌────────┐  │ │    │
│  │  │  │Enqueue│──▶│Allocate  │──▶│Preempt │──▶│Reclaim │  │ │    │
│  │  │  │       │  │          │  │        │  │        │  │ │    │
│  │  │  └──────┘  └──────────┘  └────────┘  └────────┘  │ │    │
│  │  │  确定哪些   决定 Pod      抢占低优先    回收其他  │ │    │
│  │  │  Pod 可以   放在哪个      级任务资源    队列资源  │ │    │
│  │  │  参与调度   Node 上                                  │ │    │
│  │  │                                                    │ │    │
│  │  └────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  每个阶段中的 Plugin 实现接口:                                    │
│                                                                  │
│  type Plugin interface {                                         │
│      Name() string                                               │
│      OnSessionOpen(ssn *Session) error                           │
│      OnSessionClose(ssn *Session) error                          │
│  }                                                               │
│                                                                  │
│  // 各阶段的扩展接口:                                            │
│  type EnqueuePlugin interface {                                  │
│      ReadyForExecution(ssn, obj) bool                            │
│  }                                                               │
│  type AllocatePlugin interface {                                 │
│      TaskOrderFn(l, r interface{}) bool                          │
│      JobOrderFn(l, r interface{}) bool                           │
│      PredicateFn(pod *v1.Pod, node *NodeInfo) bool               │
│      NodeOrderFn(pod *v1.Pod, node *NodeInfo) (float64, error)   │
│      BestNodeFn(pod *v1.Pod, nodes []*NodeInfo) *NodeInfo       │
│  }                                                               │
│  type PreemptPlugin interface {                                  │
│      VictimTasksFn(ssn *Session) []*v1.Pod                       │
│      PreemptableFn(preemptor, preemptee interface{}) bool        │
│  }                                                               │
│  type ReclaimPlugin interface {                                  │
│      ReclaimableFn(reclaimer, reclaimee interface{}) bool        │
│  }                                                               │
└──────────────────────────────────────────────────────────────────┘
```

### 5.4 Gang Scheduling 实现细节

```
PodGroup 创建 (minAvailable=4)
         │
         ▼
┌───────────────────────┐
│ Enqueue 阶段           │
│                       │
│ 检查队列资源是否充足  │
│ 满足 minResources?    │
│    │                  │
│    ├── 是 → 放入调度  │
│    │        活跃队列  │
│    └── 否 → 留在      │
│         Pending 状态  │
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Allocate 阶段          │
│                       │
│ 4 个 Pod 绑定到 4 个  │
│ Node，但此时全部       │
│ Pod 状态为 Pending     │
│ (全部绑定成功才提交)  │
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Bind 确认              │
│                       │
│ 所有 Pod 均绑定成功:  │
│   → PodGroup: Running │
│   → 各 Pod 变为       │
│     Schedulable       │
│                       │
│ 部分失败:              │
│   → 回滚已绑定的 Pod  │
│   → PodGroup: Pending │
│   → 重新进入调度循环  │
└───────────────────────┘
```

### 5.5 二次开发切入点

#### A. 自定义调度插件

```go
// 1. 实现 Plugin 接口
type MyCustomPlugin struct {
    // 自定义字段
    gpuTopology map[string]GPUTopology
}

func (mp *MyCustomPlugin) Name() string {
    return "my-custom-plugin"
}

func (mp *MyCustomPlugin) OnSessionOpen(ssn *framework.Session) error {
    // 注册 NodeOrder 回调：影响节点打分
    ssn.AddNodeOrderFn(mp.Name(), func(task *api.TaskInfo, node *api.NodeInfo) (float64, error) {
        // 例如：NVLink 拓扑感知打分
        score := mp.calculateGPUTopologyScore(task, node)
        return score, nil
    })

    // 注册 Predicate 回调：影响节点过滤
    ssn.AddPredicateFn(mp.Name(), func(task *api.TaskInfo, node *api.NodeInfo) error {
        // 自定义过滤逻辑
        if !mp.checkGPUAffinity(task, node) {
            return fmt.Errorf("GPU affinity not satisfied")
        }
        return nil
    })

    // 注册 JobOrder 回调：影响作业排序
    ssn.AddJobOrderFn(mp.Name(), func(l, r interface{}) bool {
        lj := l.(*api.JobInfo)
        rj := r.(*api.JobInfo)
        // 例如：按提交时间排序
        return lj.CreationTimestamp.Before(&rj.CreationTimestamp)
    })

    return nil
}

func (mp *MyCustomPlugin) OnSessionClose(ssn *framework.Session) error {
    // 清理/统计
    return nil
}

// 2. 注册插件
func init() {
    framework.RegisterPluginBuilder("my-custom-plugin", func(args *framework.PluginArguments) framework.Plugin {
        return &MyCustomPlugin{}
    })
}
```

#### B. 自定义 Queue 管理

```yaml
# 层级队列 + 资源配额
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: research-dept
spec:
  weight: 50
  capability:
    cpu: "200"
    memory: 512Gi
    nvidia.com/gpu: "32"
  reclaimable: true
---
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: production-dept
spec:
  weight: 80
  capability:
    cpu: "500"
    memory: 1Ti
    nvidia.com/gpu: "64"
  reclaimable: false
---
# Job 绑定到队列
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: distributed-bert
spec:
  queue: research-dept
  schedulerName: volcano
  minAvailable: 8
  tasks:
    - replicas: 1
      name: master
      template:
        # ...
    - replicas: 7
      name: worker
      template:
        # ...
```

#### C. 自定义 Lifecycle Policy

```yaml
# 二次开发：精细的生命周期管理
spec:
  policies:
    # 任意 Task 失败时重启
    - event: PodFailed
      action: RestartJob
      exitCode: 137  # OOMKilled
    # 所有 Task 完成时标记成功
    - event: TaskCompleted
      action: CompleteJob
    # 任意 Task Evicted 时终止
    - event: PodEvicted
      action: TerminateJob
  tasks:
    - name: worker
      replicas: 4
      policies:
        # Worker 级别的策略（覆盖 Job 级别）
        - event: PodFailed
          action: RestartTask  # 仅重启该 Task
          maxRetries: 3
```

---

## 六、三者协同的二次开发架构

### 6.1 典型 AI 平台集成架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                          AI Platform                                  │
│                                                                      │
│   用户提交:                                                          │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │  API Gateway (REST/gRPC)                                      │   │
│   │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │   │
│   │  │ 训练任务API  │  │ Pipeline API │  │ 模型服务 API       │  │   │
│   │  └──────┬──────┘  └──────┬───────┘  └────────┬───────────┘  │   │
│   └─────────┼────────────────┼────────────────────┼──────────────┘   │
│             │                │                    │                  │
│   ┌─────────▼────────────────▼────────────────────▼──────────────┐   │
│   │              Platform Controller (二次开发核心)                │   │
│   │                                                              │   │
│   │  ┌────────────────────────────────────────────────────────┐  │   │
│   │  │  1. 接收用户请求                                        │  │   │
│   │  │  2. 翻译为 Kubeflow/Argo/Volcano CR                    │  │   │
│   │  │  3. 注入调度策略（Queue/Priority/Gang）                 │  │   │
│   │  │  4. 状态聚合 → 返回用户                                 │  │   │
│   │  └────────────────────────────────────────────────────────┘  │   │
│   └───────────────────┬──────────────────────────────────────────┘   │
│                       │                                              │
│   ┌───────────────────▼──────────────────────────────────────────┐   │
│   │  Kubernetes + Volcano Scheduler                               │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │   │
│   │  │Kubeflow  │  │Argo      │  │Volcano   │                   │   │
│   │  │Operator  │  │Workflows │  │Scheduler │                   │   │
│   │  └──────────┘  └──────────┘  └──────────┘                   │   │
│   └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 完整执行流程示例

```
用户: "提交分布式 BERT 训练任务"
  │
  ▼
Platform Controller (二次开发)
  │
  ├── 1. 鉴权 + 配额检查
  │
  ├── 2. 生成 Volcano Job CR
  │      - minAvailable = worker 数
  │      - queue = 用户所属队列
  │      - schedulerName = volcano
  │
  ├── 3. 如果是 Pipeline:
  │      - 编译 KFP Pipeline → IR YAML
  │      - 翻译为 Argo Workflow CR
  │      - Workflow 中每个 Step 的 Pod:
  │        → 注入 volcano.sh/queue annotation
  │        → 创建 PodGroup (gang scheduling)
  │
  ├── 4. Apply CRs to API Server
  │
  ▼
Volcano Scheduler
  │
  ├── Enqueue: 队列配额检查 → 入队
  ├── Allocate: Gang 调度 → 绑定 Pod 到 Node
  │
  ▼
Argo Workflow Controller (如果是 Pipeline)
  │
  ├── DAG 拓扑驱动
  ├── Step 依赖执行
  ├── Artifacts 传递
  │
  ▼
Kubeflow Training Controller (如果是训练任务)
  │
  ├── 管理 Replica 生命周期
  ├── 监控训练指标
  ├── 错误恢复
  │
  ▼
训练完成 → 状态回调 → 用户查询
```

---

## 七、深度二次开发：高级设计模式

### 7.1 Webhook 鉴权 + 默认值注入

```go
// MutatingAdmissionWebhook: 自动注入调度策略
func mutatingWebhook(w http.ResponseWriter, r *http.Request) {
    admissionReview := readAdmissionReview(r)
    pod := admissionReview.Request.Object.(*corev1.Pod)

    // 自动注入 Volcano 调度注解
    if pod.Annotations == nil {
        pod.Annotations = make(map[string]string)
    }
    if _, ok := pod.Annotations["scheduling.volcano.sh/queue"]; !ok {
        pod.Annotations["scheduling.volcano.sh/queue"] = "default-ml-queue"
    }

    // 自动注入资源配额
    for i := range pod.Spec.Containers {
        container := &pod.Spec.Containers[i]
        if gpuRequest, ok := container.Resources.Requests["nvidia.com/gpu"]; ok {
            // 根据 GPU 型号自动选择 Node Selector
            pod.Spec.NodeSelector["gpu-type"] = determineGPUType(gpuRequest)
        }
    }

    // 返回 patch
    patchBytes := generatePatch(pod)
    respondWithPatch(w, admissionReview, patchBytes)
}

// ValidatingAdmissionWebhook: 校验资源请求
func validatingWebhook(w http.ResponseWriter, r *http.Request) {
    admissionReview := readAdmissionReview(r)
    job := admissionReview.Request.Object.(*volcano.Job)

    // 校验 Gang Scheduling 约束
    if job.Spec.MinAvailable != nil {
        totalReplicas := int32(0)
        for _, task := range job.Spec.Tasks {
            totalReplicas += task.Replicas
        }
        if *job.Spec.MinAvailable > totalReplicas {
            deny(w, "minAvailable cannot exceed total replicas")
            return
        }
    }

    allow(w)
}
```

### 7.2 自定义指标 + 智能调度

```go
// 采集自定义指标，注入 Volcano 调度决策
type MetricsAwarePlugin struct {
    metricsClient metricsv1beta1.MetricsV1beta1Interface
    gpuExporter   GPUExporter
}

func (p *MetricsAwarePlugin) OnSessionOpen(ssn *framework.Session) error {
    ssn.AddNodeOrderFn(p.Name(), func(task *api.TaskInfo, node *api.NodeInfo) (float64, error) {
        // 获取 GPU 利用率
        gpuUtil, err := p.gpuExporter.GetGPUUtilization(node.Name)
        if err != nil {
            return 0, err
        }

        // 获取网络带宽
        netBW, err := p.getNetworkBandwidth(node.Name)
        if err != nil {
            return 0, err
        }

        // 综合打分：偏好 GPU 利用率低、带宽高的节点
        score := (100 - gpuUtil) * 0.6 + netBW * 0.4
        return score, nil
    })

    ssn.AddBestNodeFn(p.Name(), func(task *api.TaskInfo, nodes []*api.NodeInfo) *api.NodeInfo {
        // AllReduce 场景：选择交换机亲和的节点
        return p.selectSwitchAffineNodes(task, nodes)
    })

    return nil
}
```

### 7.3 多集群调度

```yaml
# 二次开发：跨集群联邦调度
apiVersion: scheduling.volcano.sh/v1alpha1
kind: FederatedJob
metadata:
  name: global-training
spec:
  placement:
    clusters:
      - name: gpu-cluster-bj
        minReplicas: 4
        maxReplicas: 8
        priority: high
      - name: gpu-cluster-sh
        minReplicas: 2
        maxReplicas: 4
        priority: medium
  template:
    # ...Job Template
  orchestration:
    # 通信拓扑
    communication: NCCL
    # 数据并行 + 模型并行策略
    strategy: DataParallel
    # 跨集群带宽感知
    bandwidthAware: true
```

### 7.4 Argo + Volcano 联动的 DAG Pipeline

```yaml
# Argo Workflow 中每个节点都通过 Volcano Gang 调度
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: ml-pipeline
spec:
  entrypoint: training-pipeline
  templates:
    - name: training-pipeline
      dag:
        tasks:
          - name: data-prep
            template: data-prep-step
          - name: train
            template: distributed-train
            dependencies: [data-prep]
          - name: evaluate
            template: evaluate-step
            dependencies: [train]
          - name: deploy
            template: deploy-model
            dependencies: [evaluate]

    - name: distributed-train
      # Argo 管理 DAG 依赖，Volcano 管理 Gang 调度
      plugin:
        volcano:
          apiVersion: batch.volcano.sh/v1alpha1
          kind: Job
          metadata:
            name: "{{workflow.name}}-train"
            annotations:
              # 关键：通过 annotation 让 Volcano 接管调度
              scheduling.volcano.sh/queue: "ml-training-queue"
          spec:
            minAvailable: 4
            schedulerName: volcano
            queue: ml-training-queue
            tasks:
              - name: ps
                replicas: 2
                template:
                  # ...
              - name: worker
                replicas: 4
                template:
                  # ...
```

---

## 八、二次开发工程实践

### 8.1 项目结构

```
ai-platform/
├── api/                          # CRD 定义
│   ├── v1alpha1/
│   │   ├── trainingjob_types.go
│   │   ├── pipeline_types.go
│   │   └── zz_generated.deepcopy.go
│   └── v1beta1/
│       └── ...
├── cmd/
│   ├── manager/                  # Controller 入口
│   │   └── main.go
│   └── scheduler-plugin/         # Volcano 插件入口
│       └── main.go
├── internal/
│   ├── controller/               # Controller 逻辑
│   │   ├── trainingjob_controller.go
│   │   ├── pipeline_controller.go
│   │   └── reconciler.go
│   ├── scheduler/                # 调度插件
│   │   ├── gpu_topology.go
│   │   ├── bandwidth_aware.go
│   │   └── custom_score.go
│   ├── webhook/                  # Admission Webhook
│   │   ├── mutating.go
│   │   └── validating.go
│   └── translator/               # CR 转换层
│       ├── kfp_to_argo.go
│       ├── argo_to_volcano.go
│       └── volcano_injector.go
├── deploy/
│   ├── crd/
│   ├── rbac/
│   ├── webhook/
│   └── config/
├── test/
│   ├── e2e/
│   ├── integration/
│   └── unit/
└── Makefile
```

### 8.2 Controller 单元测试模式

```go
func TestTrainingJobReconcile(t *testing.T) {
    scheme := runtime.NewScheme()
    _ = v1alpha1.AddToScheme(scheme)
    _ = corev1.AddToScheme(scheme)

    t.Run("creates volcano job when training job submitted", func(t *testing.T) {
        // 准备：模拟用户创建的 TrainingJob
        trainingJob := &v1alpha1.TrainingJob{
            ObjectMeta: metav1.ObjectMeta{
                Name:      "bert-training",
                Namespace: "default",
            },
            Spec: v1alpha1.TrainingJobSpec{
                Framework:   "pytorch",
                Replicas:    4,
                Image:       "my-registry/bert:v1",
                Queue:       "ml-queue",
                GangScheduling: true,
            },
        }

        // 构造 fake client
        fakeClient := fake.NewClientBuilder().
            WithScheme(scheme).
            WithObjects(trainingJob).
            WithStatusSubresource(trainingJob).
            Build()

        reconciler := &TrainingJobReconciler{
            Client:   fakeClient,
            Scheme:   scheme,
            Recorder: record.NewFakeRecorder(100),
        }

        // 执行 Reconcile
        result, err := reconciler.Reconcile(context.Background(), ctrl.Request{
            NamespacedName: types.NamespacedName{
                Name: "bert-training", Namespace: "default",
            },
        })

        // 验证
        require.NoError(t, err)
        assert.False(t, result.Requeue)

        // 验证 Volcano Job 被创建
        volcanoJob := &volcano.Job{}
        err = fakeClient.Get(context.Background(), types.NamespacedName{
            Name: "bert-training", Namespace: "default",
        }, volcanoJob)
        require.NoError(t, err)
        assert.Equal(t, int32(4), volcanoJob.Spec.Tasks[0].Replicas)
        assert.Equal(t, "ml-queue", volcanoJob.Spec.Queue)
        assert.Equal(t, int32(4), *volcanoJob.Spec.MinAvailable)

        // 验证 PodGroup 被创建
        podGroup := &scheduling.PodGroup{}
        err = fakeClient.Get(context.Background(), types.NamespacedName{
            Name: "bert-training", Namespace: "default",
        }, podGroup)
        require.NoError(t, err)
    })

    t.Run("handles gang scheduling failure gracefully", func(t *testing.T) {
        // ...模拟部分节点不足的情况
    })
}
```

---

## 九、关键设计决策总结

| 维度 | Kubeflow | Argo Workflows | Volcano |
|------|----------|----------------|---------|
| **核心抽象** | Training Job (框架级) | Workflow (DAG编排) | Queue + PodGroup (资源调度) |
| **扩展机制** | CRD + Backend Plugin | Template + Executor + Plugin | Scheduler Plugin Framework |
| **二次开发重点** | 新框架集成、Pipeline SDK 扩展 | 自定义 Executor、Artifact Driver、Template 类型 | 调度算法、Queue 管理、GPU 拓扑感知 |
| **状态管理** | Replica 级聚合 | DAG 节点级状态机 | Job/Task/PodGroup 三级状态 |
| **与 K8s 集成深度** | 中（主要管理 Pod 生命周期） | 中（管理 Pod + PVC） | 深（直接调度层扩展） |
| **适用场景** | ML 训练/服务全生命周期 | 通用 DAG 工作流 | 大规模批量调度 + 资源隔离 |

**核心原则：**
1. **Kubeflow** 二次开发重在 **训练框架抽象** 和 **Pipeline SDK 生态**
2. **Argo** 二次开发重在 **执行器扩展** 和 **模板复用体系**
3. **Volcano** 二次开发重在 **调度算法插件** 和 **资源管理策略**
4. 三者联动时，核心难点在于 **统一状态管理** 和 **调度策略注入**
