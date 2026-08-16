---
title: Kubernetes 底层细节深度解析
date: 2026-09-07 17:45:00
tags:
  - Kubernetes
  - etcd
  - kubelet
  - 调度器
categories:
  - Kubernetes
---

## 一、Kubernetes 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     Control Plane (控制平面)              │
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐   │
│  │ kube-api     │ │ etcd         │ │ kube-scheduler │   │
│  │ server       │ │ (分布式KV存储)│ │ (调度器)        │   │
│  │ (API网关)    │ │              │ │                │   │
│  └──────┬───────┘ └──────────────┘ └────────────────┘   │
│         │                                               │
│  ┌──────┴───────┐ ┌──────────────────────────────────┐  │
│  │ controller   │ │ cloud-controller-manager         │  │
│  │ manager      │ │ (云厂商适配层)                    │  │
│  │ (控制器管理器)│ │                                  │  │
│  └──────────────┘ └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         │ API Server
                         │ (唯一入口)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                     Worker Node (工作节点)                │
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐   │
│  │ kubelet      │ │ kube-proxy   │ │ Container      │   │
│  │ (节点代理)   │ │ (网络代理)   │ │ Runtime        │   │
│  │              │ │              │ │ (容器运行时)    │   │
│  └──────────────┘ └──────────────┘ └────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │              Pod ← Pod ← Pod                        ││
│  │        (最小调度单元，包含一个或多个容器)              ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 二、API Server 底层机制

API Server 是整个 K8s 的**唯一入口**，所有组件都只与 API Server 通信。

### 1. 请求处理链路

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────────────┐
│             API Server 请求处理流程               │
│                                                  │
│  ① Authentication（认证）                        │
│     ├── X.509 证书认证                            │
│     ├── ServiceAccount Token (JWT)               │
│     ├── OIDC Token                               │
│     └── Webhook Token 认证                       │
│                                                  │
│  ② Authorization（授权）                         │
│     ├── RBAC（基于角色的访问控制）                  │
│     ├── ABAC（基于属性的访问控制）                  │
│     └── Webhook 授权                             │
│                                                  │
│  ③ Admission Control（准入控制）                  │
│     ├── MutatingAdmissionWebhook（变更型）         │
│     │   └── 可以修改请求对象（如注入 sidecar）      │
│     └── ValidatingAdmissionWebhook（验证型）       │
│         └── 只做校验，不可修改                     │
│                                                  │
│  ④ Schema Validation（模式校验）                  │
│     └── OpenAPI Schema 校验字段类型/必填项          │
│                                                  │
│  ⑤ 持久化到 etcd                                 │
│     └── 写入成功返回 200/201                      │
└─────────────────────────────────────────────────┘
```

### 2. API Server 的 Watch 机制（核心）

```go
// API Server 基于 HTTP Chunked Transfer 实现 Watch
// 这是整个 K8s 事件驱动架构的基础

// 客户端（如 kubelet、controller-manager）发起 Watch 请求：
GET /api/v1/namespaces/default/pods?watch=true&resourceVersion=12345

// 服务端返回流式响应（chunked encoding）：
// 每当 etcd 中的资源发生变化，API Server 立即推送事件
{"type":"ADDED","object":{...pod...}}
{"type":"MODIFIED","object":{...pod...}}
{"type":"DELETED","object":{...pod...}}

// 底层实现：
// 1. API Server 维护一个 WatchCache（环形缓冲区）
//    - 存储最近 N 个版本的资源对象
//    - 新 Watch 请求可从 cache 中指定版本开始
// 2. etcd 的 Watch → API Server 的 WatchCache → 客户端的 Watch
//    形成两级 Watch 缓存链
```

```go
// WatchCache 核心数据结构（API Server 源码）：
type WatchCache struct {
    sync.RWMutex
    
    // 环形缓冲区，存储资源变更历史
    cache      []*watchCacheEvent  // 固定大小的环形数组
    cacheSize  int                  // 缓存容量
    startIndex int                  // 起始版本号
    endIndex   int                  // 结束版本号
    
    // 资源的完整存储（用于 List 请求）
    store      cache.Store
    
    // 所有 Watcher 的列表
    watchers   map[int]*cacheWatcher
}

// 当 etcd 有变更时：
func (w *WatchCache) processEvent(event watch.Event) {
    w.Lock()
    defer w.Unlock()
    
    // 1. 更新环形缓冲区
    w.cache[w.endIndex % w.cacheSize] = &watchCacheEvent{...}
    w.endIndex++
    
    // 2. 通知所有 Watcher
    for _, watcher := range w.watchers {
        watcher.add(event)
    }
}
```

---

## 三、etcd 底层机制

### 1. 存储模型

```go
// etcd 是一个分布式 KV 存储，底层使用：
// - Raft 共识协议（保证一致性）
// - bbolt（B+ Tree，磁盘持久化）

// K8s 资源在 etcd 中的 Key 格式：
// /registry/{resource-type}/{namespace}/{name}

// 示例：
/registry/pods/default/nginx-pod-abc123
/registry/deployments/default/nginx-deployment
/registry/services/default/nginx-service
/registry/secrets/default/my-secret

// bbolt 存储结构：
// Bucket → Key → Value
// 每个 resource-type 是一个 Bucket
// Key 是 namespace/name
// Value 是 protobuf 序列化的资源对象
```

### 2. Raft 协议核心

```
Raft 三阶段：
┌─────────────────────────────────────────────┐
│              Leader Election                 │
│                                              │
│  ① 节点启动 → Follower 状态                  │
│  ② 超时未收到心跳 → 转为 Candidate            │
│  ③ 发起投票，获得多数同意 → 转为 Leader       │
│  ④ Leader 定期发送心跳维持权威                │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│              Log Replication                 │
│                                              │
│  ① 客户端写请求 → Leader                     │
│  ② Leader 追加到本地日志                      │
│  ③ Leader 并行复制到所有 Follower             │
│  ④ 多数节点确认 → 提交（committed）           │
│  ⑤ Leader 通知 Follower 提交                 │
│  ⑥ 应用到状态机（写入 bbolt）                 │
└─────────────────────────────────────────────┘

// 一致性保证：
// - 强一致性读（linearizable）：必须经过 Leader 确认
// - 顺序一致性读：直接从本地读取（可能读到旧数据）
// K8s 默认使用 linearizable 读
```

---

## 四、Scheduler（调度器）底层

### 调度流程：Filter → Score → Bind

```
Pod 调度完整流程：

┌──────────────────────────────────────────────────┐
│  ① 监听未调度的 Pod                                │
│     (通过 Watch 机制，发现 spec.nodeName 为空的 Pod) │
│                                                    │
│  ② 过滤阶段（Filter/Predicate）                     │
│     ├── NodeResourcesFit: 资源是否充足              │
│     ├── NodeAffinity: 节点亲和性                    │
│     ├── PodToleratesNodeTaints: 污点容忍           │
│     ├── NodePorts: 端口是否冲突                     │
│     ├── PodTopologySpread: 拓扑分布约束             │
│     └── VolumeZone: 存储卷区域限制                  │
│     → 输出：可行节点列表                             │
│                                                    │
│  ③ 打分阶段（Score/Priority）                      │
│     ├── LeastRequestedPriority: 资源空闲最多的节点   │
│     ├── MostRequestedPriority: 资源使用最多的节点    │
│     ├── BalancedResourceAllocation: CPU/Mem 均衡    │
│     ├── InterPodAffinity: Pod 间亲和/反亲和         │
│     ├── NodePreferAvoidPods: 节点偏好               │
│     └── ImageLocality: 镜像是否已存在               │
│     → 输出：每个可行节点的加权总分                    │
│                                                    │
│  ④ 绑定阶段（Bind）                                │
│     → 选择得分最高的节点，通过 API Server            │
│       将 Pod.spec.nodeName 设置为目标节点            │
└──────────────────────────────────────────────────┘
```

```go
// 调度器核心框架（Scheduling Framework）：
// 将调度过程抽象为一系列扩展点（Extension Points）

type Plugin interface {
    Name() string
}

// PreFilter: 预处理，计算共享状态
type PreFilterPlugin interface {
    PreFilter(ctx context.Context, state *CycleState, p *v1.Pod) (*PreFilterResult, *Status)
}

// Filter: 过滤不可行节点
type FilterPlugin interface {
    Filter(ctx context.Context, state *CycleState, pod *v1.Pod, nodeInfo *NodeInfo) *Status
}

// Score: 对可行节点打分
type ScorePlugin interface {
    Score(ctx context.Context, state *CycleState, p *v1.Pod, nodeName string) (int64, *Status)
    ScoreExtensions() ScoreExtensions  // NormalizeScore
}

// Reserve: 为 Pod 预留资源
type ReservePlugin interface {
    Reserve(ctx context.Context, state *CycleState, p *v1.Pod, nodeName string) *Status
}

// Permit: 准入审批（用于 Gang Scheduling 等场景）
type PermitPlugin interface {
    Permit(ctx context.Context, state *CycleState, p *v1.Pod, nodeName string) (*Status, time.Duration)
}

// Bind: 执行绑定
type BindPlugin interface {
    Bind(ctx context.Context, state *CycleState, p *v1.Pod, nodeName string) *Status
}

// PostBind: 绑定后的清理工作
type PostBindPlugin interface {
    PostBind(ctx context.Context, state *CycleState, p *v1.Pod, nodeName string)
}
```

### 调度队列

```go
// 调度器内部使用三级优先队列：
type PriorityQueue struct {
    // 活跃队列：新创建的 Pod，按优先级排序
    activeQ *heap.Heap
    
    // 不可调度队列：之前调度失败的 Pod
    // 按退避时间排队，避免频繁重试
    unschedulableQ *UnschedulablePodsMap
    
    // Backoff 队列：退避时间到期的 Pod
    // 从 unschedulableQ 移到这里等待重新调度
    podBackoffQ *heap.Heap
}

// 调度循环：
for {
    // 1. 从 activeQ 取出优先级最高的 Pod
    pod := activeQ.Pop()
    
    // 2. 执行调度（Filter → Score → Bind）
    result := schedule(pod)
    
    // 3. 如果失败：
    if result.err != nil {
        if result.reason == Unschedulable {
            // 放入不可调度队列
            unschedulableQ.Add(pod)
        } else if result.reason == UnschedulableAndUnresolvable {
            // 不可调度且无法解决，直接标记失败
            rejectPod(pod)
        }
    }
}
```

---

## 五、Controller Manager 底层

### 核心模式：声明式 API + 控制循环（Reconcile Loop）

```
┌──────────────────────────────────────────────┐
│           控制循环（Control Loop）              │
│                                              │
│    ┌─────────┐                               │
│    │ Observe │ ① 观测：Watch API Server      │
│    │ (观测)  │    获取资源当前状态              │
│    └────┬────┘    (Actual State)              │
│         │                                    │
│    ┌────▼────┐                               │
│    │ Diff    │ ② 分析：对比期望状态与实际状态   │
│    │ (分析)  │    (Desired State vs Actual)    │
│    └────┬────┘                               │
│         │                                    │
│    ┌────▼────┐                               │
│    │ Act     │ ③ 执行：采取行动使实际状态       │
│    │ (执行)  │    趋近于期望状态                │
│    └─────────┘                               │
│                                              │
│    不断循环，直到 Actual == Desired            │
└──────────────────────────────────────────────┘
```

### Deployment → ReplicaSet → Pod 的级联控制

```
┌──────────────────────────────────────────────────────────┐
│  Deployment Controller 控制循环                            │
│                                                          │
│  用户声明：replicas: 3, image: nginx:1.25                 │
│                                                          │
│  ① Deployment Controller Watch 到 Deployment 对象变化      │
│  ② 检查当前 ReplicaSet 状态                                │
│  ③ 如果需要滚动更新：                                      │
│     a. 创建新版 ReplicaSet（revision+1）                   │
│     b. 逐步扩容新 RS，缩容旧 RS                            │
│        maxSurge=25% → 最多多创建 1 个 Pod                  │
│        maxUnavailable=25% → 最多少 1 个 Pod                │
│     c. 每次操作后等待 Pod Ready                            │
│  ④ 保持最终状态与期望一致                                   │
│                                                          │
│  ReplicaSet Controller 控制循环：                          │
│  ① Watch 到 ReplicaSet 对象变化                            │
│  ② 对比 spec.replicas 与实际 Pod 数量                      │
│  ③ 数量不足 → 创建 Pod                                     │
│  ④ 数量过多 → 删除 Pod（默认按 Pod 年龄排序）               │
└──────────────────────────────────────────────────────────┘
```

### Informer 机制（所有 Controller 的基石）

```go
// 所有 Controller 都使用 SharedInformer 机制
// 核心目的：减少对 API Server 的 Watch 请求

type SharedInformerFactory interface {
    // 所有 Controller 共享同一个 Watch 连接
    Core().V1().Pods()           // → PodInformer
    Apps().V1().Deployments()    // → DeploymentInformer
    Apps().V1().ReplicaSets()    // → ReplicaSetInformer
}

// Informer 内部机制：
┌─────────────────────────────────────────────────┐
│                 Informer 架构                    │
│                                                  │
│  ┌──────────────┐     ┌──────────────────┐      │
│  │ Reflector    │     │ Delta FIFO Queue │      │
│  │ (Watch +     │────>│ (事件队列)        │      │
│  │  List 同步)  │     │                  │      │
│  └──────────────┘     └────────┬─────────┘      │
│                               │                 │
│                      ┌────────▼─────────┐       │
│                      │   Processor      │       │
│                      │ (事件处理器)       │       │
│                      └────────┬─────────┘       │
│                               │                 │
│              ┌────────────────┼────────────┐    │
│              │                │             │    │
│    ┌─────────▼──────┐ ┌──────▼──────┐ ┌───▼──┐ │
│    │ Informer Cache │ │ Resource    │ │ 用户  │ │
│    │ (本地全量缓存)  │ │ Event Handler│ │ Handler│ │
│    │                │ │ (OnAdd,     │ │(业务  │ │
│    │ = 缓存的 List  │ │  OnUpdate,  │ │ 逻辑) │ │
│    │   数据源       │ │  OnDelete)  │ │       │ │
│    └────────────────┘ └─────────────┘ └──────┘ │
└─────────────────────────────────────────────────┘

// 核心流程：
// 1. 启动时执行 List（全量拉取）→ 填充本地缓存
// 2. 后续通过 Watch（增量更新）→ 维护缓存一致性
// 3. Controller 的 List/Get 操作直接读取本地缓存
//    而非每次都请求 API Server
// 4. 事件通过 Handler 分发给各 Controller
```

```go
// Informer 的典型使用：
func NewDeploymentController(client kubernetes.Interface) {
    factory := informers.NewSharedInformerFactory(client, 30*time.Second)
    
    deployInformer := factory.Apps().V1().Deployments().Informer()
    rsInformer := factory.Apps().V1().ReplicaSets().Informer()
    podInformer := factory.Core().V1().Pods().Informer()
    
    // 注册事件处理器
    deployInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
        AddFunc:    func(obj interface{}) { /* 新 Deployment 创建 */ },
        UpdateFunc: func(oldObj, newObj interface{}) { /* Deployment 更新 */ },
        DeleteFunc: func(obj interface{}) { /* Deployment 删除 */ },
    })
    
    // 启动所有 Informer
    factory.Start(wait.NeverStop)
    // 等待本地缓存同步完成
    factory.WaitForCacheSync(wait.NeverStop)
}
```

---

## 六、kubelet 底层机制

### 1. Pod 管理全流程

```
kubelet 核心循环（PLEG 模型）：

┌─────────────────────────────────────────────────────┐
│                    kubelet                            │
│                                                      │
│  ┌────────────┐                                     │
│  │ SyncLoop   │ ← 核心主循环                         │
│  │            │                                     │
│  │ 监听事件源：│                                     │
│  │ ① configCh │ ← API Server 下发的 Pod 配置         │
│  │ ② plegCh   │ ← 容器运行时事件（容器启停/死亡）      │
│  │ ③ syncCh   │ ← 定时同步（默认每 1 秒）             │
│  │ ④ housekeep│ ← 清理任务                           │
│  │ ⑤ liveness │ ← 健康检查结果                       │
│  └─────┬──────┘                                     │
│        │                                            │
│  ┌─────▼──────┐                                     │
│  │ SyncPod    │ ← 核心同步逻辑                       │
│  │            │                                     │
│  │ 1. 计算 Pod 变更：                                │
│  │    对比 desired state vs actual state             │
│  │                                                  │
│  │ 2. 执行操作：                                     │
│  │    ├── 创建 Pod sandbox（网络命名空间）             │
│  │    ├── 拉取镜像                                   │
│  │    ├── 创建 Init 容器（按顺序执行）                │
│  │    ├── 创建业务容器（并行）                        │
│  │    ├── 执行 startup/liveness/readiness 探针       │
│  │    └── 挂载 Volume                               │
│  └────────────┘                                     │
└─────────────────────────────────────────────────────┘
```

### 2. PLEG（Pod Lifecycle Event Generator）

```go
// PLEG 的核心职责：将容器运行时的底层事件转换为 Pod 级别的事件

// 底层实现：
type GenericPLEG struct {
    runtime  kubecontainer.Runtime  // 容器运行时接口
    eventChannel chan *PodLifecycleEvent
}

// 工作流程（基于 Relist 模式）：
// 1. 每隔 relistPeriod（默认 1 秒）执行一次 Relist
func (g *GenericPLEG) Relist() {
    // a. 获取所有容器的当前状态
    pods := g.runtime.ListPods()     // 通过 CRI 接口
    allContainers := getAllContainers(pods)
    
    // b. 与上次快照对比
    for uid, containers := range allContainers {
        oldContainers := g.podRecords.getPrevious(uid)
        
        // c. 生成事件
        for id, container := range containers {
            old, exists := oldContainers[id]
            if !exists {
                // 新容器 → 生成 ContainerStarted 事件
                events = append(events, generateEvent(uid, ContainerStarted))
            } else if old.State != container.State {
                // 状态变更 → 生成对应事件
                events = append(events, generateStateEvent(uid, container))
            }
        }
    }
    
    // d. 发送到 eventChannel → SyncLoop 消费
    for _, event := range events {
        g.eventChannel <- event
    }
    
    // e. 更新缓存
    g.podRecords.update(allContainers)
}
```

### 3. CRI（Container Runtime Interface）

```
kubelet 与容器运行时的交互：

kubelet ──gRPC──> CRI Shim ──> 容器运行时（containerd / CRI-O）

┌──────────────────────────────────────────────────┐
│              CRI gRPC 接口                        │
│                                                  │
│  RuntimeService（容器生命周期管理）：               │
│  ├── RunPodSandbox(podConfig)                    │
│  │   └── 创建 Pod 级别的 namespace（net, pid）     │
│  ├── StopPodSandbox(podSandboxId)                │
│  ├── RemovePodSandbox(podSandboxId)              │
│  ├── CreateContainer(podSandboxId, containerCfg) │
│  ├── StartContainer(containerId)                 │
│  ├── StopContainer(containerId, timeout)         │
│  ├── RemoveContainer(containerId)                │
│  ├── ListContainers(filter)                      │
│  ├── ListPodSandbox(filter)                      │
│  ├── ContainerStatus(containerId)                │
│  ├── PodSandboxStatus(podSandboxId)              │
│  ├── ExecSync(containerId, cmd, timeout)         │
│  └── Attach(containerId, stdin, stdout, stderr)  │
│                                                  │
│  ImageService（镜像管理）：                        │
│  ├── ListImages(filter)                          │
│  ├── ImageStatus(image)                          │
│  ├── PullImage(image, auth)                      │
│  └── RemoveImage(image)                          │
└──────────────────────────────────────────────────┘

// 实际调用示例（kubelet 创建 Pod）：
// 1. RunPodSandbox → 创建 pause 容器（持有网络命名空间）
// 2. 挂载 Volume（CSI）
// 3. 配置网络（CNI）
// 4. CreateContainer → 在 sandbox 内创建业务容器
// 5. StartContainer → 启动容器
```

### 4. 健康检查探针底层

```go
// kubelet 对每种探针使用独立的 Worker 管理器

// Liveness Probe（存活探针）：
// - 失败 → kubelet 杀死容器，按 restartPolicy 重启
// - 实现：probemanager.go
type manager struct {
    workers    map[probeKey]*worker    // 每个容器一个 worker
    prober     *prober                  // 实际执行探测
}

type worker struct {
    // 定时执行探测
    period time.Duration  // initialDelay + period
    
    // 探测方法：
    // 1. HTTP GET → net/http.Get(url), 检查状态码 200-399
    // 2. TCP Socket → net.DialTimeout("tcp", host:port)
    // 3. Exec → 调用 CRI 的 ExecSync，检查退出码 == 0
    // 4. gRPC → 建立 gRPC 连接，检查服务健康状态
}

// 探测结果处理：
func (w *worker) run() {
    ticker := time.NewTicker(w.period)
    for {
        select {
        case <-ticker.C:
            result := w.probe.probe(w.pod, w.container, w.containerID)
            switch result {
            case results.Success:
                w.resultManager.Set(w.probeType, w.containerID, results.Success)
            case results.Failure:
                w.resultManager.Set(w.probeType, w.containerID, results.Failure)
                if w.probeType == liveness {
                    // 触发容器重启
                    w.manager.SetPodStatus(pod, status)
                }
            }
        }
    }
}
```

---

## 七、kube-proxy 与 Service 网络底层

### Service 实现模式对比

```
┌──────────────────────────────────────────────────────────┐
│                三种代理模式                                 │
│                                                          │
│  ① iptables 模式（默认）                                  │
│     ├── 为每个 Service 创建 iptables 规则                  │
│     ├── DNAT: ClusterIP → 后端 Pod IP                     │
│     ├── 随机负载均衡（基于 iptables statistic 模块）        │
│     └── 缺点：Service 数量多时规则膨胀，性能下降             │
│                                                          │
│  ② IPVS 模式                                              │
│     ├── 基于 Linux 内核 IPVS 模块                          │
│     ├── 在内核空间做 DNAT + 负载均衡                       │
│     ├── 支持多种负载均衡算法：                               │
│     │   rr (轮询), wrr (加权轮询), lc (最少连接),          │
│     │   sh (源地址哈希), dh (目标地址哈希)                   │
│     └── 适合大规模 Service 场景（规则 O(1) 查找）            │
│                                                          │
│  ③ nftables 模式（K8s 1.29+ 实验性）                       │
│     ├── 替代 iptables 的新一代 Linux 防火墙框架              │
│     ├── 规则查找效率更高                                    │
│     └── 解决 iptables 规则膨胀问题                          │
└──────────────────────────────────────────────────────────┘
```

### iptables 模式底层实现

```bash
# kube-proxy 为每个 Service 生成如下 iptables 规则：

# 1. Service ClusterIP 的 DNAT 规则
# 当目标地址为 10.96.0.10:80 时，DNAT 到后端 Pod
iptables -t nat -A KUBE-SERVICES -d 10.96.0.10/32 -p tcp --dport 80 \
    -j KUBE-SVC-XXXX

# 2. 负载均衡：随机选择后端
# 使用 iptables statistic 模块实现随机概率选择
iptables -t nat -A KUBE-SVC-XXXX -m statistic --mode random --probability 0.333 \
    -j KUBE-SEP-AAA    # Pod A: 10.244.0.5:80
iptables -t nat -A KUBE-SVC-XXXX -m statistic --mode random --probability 0.500 \
    -j KUBE-SEP-BBB    # Pod B: 10.244.1.3:80
iptables -t nat -A KUBE-SVC-XXXX \
    -j KUBE-SEP-CCC    # Pod C: 10.244.2.7:80

# 3. 每个 SEP（Service Endpoint）的 DNAT 规则
iptables -t nat -A KUBE-SEP-AAA -p tcp -j DNAT --to-destination 10.244.0.5:80

# 4. hairpin（发夹）规则：Pod 访问自己的 Service
iptables -t nat -A KUBE-SEP-AAA -s 10.244.0.5/32 \
    -j KUBE-MARK-MASQ   # 标记需要 SNAT

# 5. MASQUERADE（SNAT）：解决 Pod 访问自身 Service 的回环问题
iptables -t nat -A KUBE-POSTROUTING -m mark --mark 0x4000/0x4000 \
    -j MASQUERADE
```

### IPVS 模式底层实现

```go
// kube-proxy 使用 netlink 调用 IPVS 内核接口

// 1. 创建 IPVS 虚拟服务器（对应 Service ClusterIP）
ipvs.AddVirtualServer(&VirtualServer{
    Address:   net.ParseIP("10.96.0.10"),
    Port:      80,
    Protocol:  "TCP",
    Scheduler: "rr",  // 轮询负载均衡
})

// 2. 添加真实服务器（对应后端 Pod）
ipvs.AddRealServer(virtualServer, &RealServer{
    Address: net.ParseIP("10.244.0.5"),
    Port:    80,
    Weight:  1,
})
ipvs.AddRealServer(virtualServer, &RealServer{
    Address: net.ParseIP("10.244.1.3"),
    Port:    80,
    Weight:  1,
})

// 底层数据结构（内核空间）：
// - 虚拟服务器：哈希表查找 O(1)
// - 真实服务器：链表（按算法选择）
// - 连接跟踪：高效复用已建立的映射关系
```

### EndpointSlice（替代 Endpoints 的新机制）

```go
// 旧版 Endpoints：一个 Service 对应一个 Endpoints 对象
// 当后端 Pod 很多时，Endpoints 对象非常大
// 每次变更都需全量传播给所有 Watch 者 → 性能瓶颈

// 新版 EndpointSlice（K8s 1.21+ GA）：
// 一个 Service 可以有多个 EndpointSlice
// 每个 Slice 最多包含 100 个 Endpoint（可配置）

type EndpointSlice struct {
    // 标记属于哪个 Service
    Labels map[string]string  // kubernetes.io/service-name=nginx
    
    // 地址类型
    AddressType AddressType  // IPv4 / IPv6 / FQDN
    
    // 端点列表（最大 100 个）
    Endpoints []Endpoint
    Ports     []EndpointPort
}

type Endpoint struct {
    Addresses []string           // Pod IP 列表
    Conditions EndpointConditions // Ready/Serving/Terminating
    NodeName   *string           // 所在节点
    Zone       *string           // 所在可用区
    Topology   map[string]string // 拓扑标签
}

// 优势：
// - 增量更新：只传播变更的 Slice，不传播整个列表
// - 支持拓扑感知路由：将流量优先路由到同区域的 Pod
// - 支持双栈（IPv4 + IPv6）
```

---

## 八、网络模型底层

### Pod 网络原理

```
每个 Pod 拥有独立的网络命名空间：

┌───────────────────────────────────────────────────────────┐
│                    Node (节点)                              │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              host network namespace                  │   │
│  │                                                     │   │
│  │    eth0 (Node IP: 192.168.1.10)                     │   │
│  │       │                                             │   │
│  │    cbr0 / flannel.1 / cilium_host (桥接/VXLAN/BPF) │   │
│  │       │         │          │                        │   │
│  │       │         │          │                        │   │
│  │  ┌────┴──┐  ┌───┴───┐  ┌──┴────┐                   │   │
│  │  │ veth  │  │ veth  │  │ veth  │                    │   │
│  │  │ pair  │  │ pair  │  │ pair  │                    │   │
│  │  └──┬────┘  └──┬────┘  └──┬────┘                   │   │
│  └─────┼──────────┼──────────┼────────────────────────┘   │
│        │          │          │                             │
│  ┌─────┼──────────┼──────────┼────────────────────────┐   │
│  │     │    Pod Network Namespace                       │   │
│  │     │          │          │                          │   │
│  │  ┌──┴───┐  ┌──┴───┐  ┌──┴───┐                      │   │
│  │  │ eth0 │  │ eth0 │  │ eth0 │                       │   │
│  │  │10.244 │  │10.244│  │10.244│                      │   │
│  │  │.0.5  │  │.0.6 │  │.1.3 │                        │   │
│  │  └──────┘  └──────┘  └──────┘                      │   │
│  │  Pod A     Pod B      Pod C                         │   │
│  └────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

### CNI（Container Network Interface）

```go
// CNI 插件执行流程（kubelet 通过 CRI 调用）：

// 1. kubelet 调用 CRI RunPodSandbox()
// 2. CRI Runtime 调用 CNI 插件
// 3. CNI 配置文件位于 /etc/cni/net.d/

// CNI 插件接口：
type CNI interface {
    AddNetworkList(net *NetworkConfig, rt *RuntimeConf) (Result, error)
    DelNetworkList(net *NetworkConfig, rt *RuntimeConf) error
    CheckNetworkList(net *NetworkConfig, rt *RuntimeConf) error
}

// AddNetwork 流程：
// 输入：
//   - Container ID
//   - Network namespace path (/proc/{pid}/ns/net)
//   - Network configuration (从 /etc/cni/net.d/ 读取)
//   - Extra args (Pod name, namespace, etc.)

// 执行步骤：
// 1. 创建 veth pair
//    ip link add veth0 type veth peer name eth0
// 2. 将 eth0 放入 Pod 的网络命名空间
//    ip link set eth0 netns {pod-netns}
// 3. 在 Pod 内配置 IP
//    ip netns exec {pod-netns} ip addr add 10.244.0.5/24 dev eth0
//    ip netns exec {pod-netns} ip link set eth0 up
//    ip netns exec {pod-netns} ip route add default via 10.244.0.1
// 4. 在 host 端配置 veth
//    ip link set veth0 up
//    brctl addif cbr0 veth0    // 加入网桥

// 输出：
//   - 分配的 IP 地址
//   - DNS 配置
//   - 路由信息
```

### 不同 CNI 插件的底层差异

```
┌──────────────────────────────────────────────────────────────┐
│                    CNI 插件对比                                │
│                                                              │
│  Flannel:                                                    │
│  ├── VXLAN 模式：在 UDP 包上封装 VXLAN 头部                   │
│  │   原始包 → VXLAN 头 → UDP 头 → IP 头 → 以太网帧            │
│  ├── host-gw 模式：直接在主机路由表写入目标 Pod 的下一跳         │
│  │   （要求所有节点在同一二层网络）                              │
│  └── 性能：VXLAN ~5-10% 损耗，host-gw 几乎无损耗              │
│                                                              │
│  Calico:                                                     │
│  ├── BGP 模式：使用 BGP 协议在节点间交换路由                    │
│  │   每个节点是 BGP Speaker，Pod 路由通过 BGP 传播             │
│  ├── IPIP 模式：IP-in-IP 隧道封装（跨子网时使用）              │
│  ├── 数据面可选：                                            │
│  │   ├── iptables（传统）                                    │
│  │   ├── eBPF（高性能）                                      │
│  │   └── VPP（向量数据包处理）                                │
│  └── 支持 NetworkPolicy（基于 iptables/eBPF 实现）             │
│                                                              │
│  Cilium:                                                     │
│  ├── 纯 eBPF 实现（绕过 iptables 和 kube-proxy）              │
│  ├── 内核级别的数据包处理，性能极高                             │
│  ├── L3/L4/L7 网络策略                                       │
│  ├── 透明加密（WireGuard/IPsec）                              │
│  └── Service Mesh 能力（替代 sidecar）                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 九、Volume 与 CSI 存储底层

### CSI（Container Storage Interface）架构

```
┌───────────────────────────────────────────────────────┐
│                    CSI 架构                            │
│                                                       │
│  kubelet                                              │
│    │                                                  │
│    │ gRPC (Unix Socket)                               │
│    ▼                                                  │
│  ┌──────────────────────┐                            │
│  │ CSI Node Driver      │ ← 运行在每个节点            │
│  │ (Node Plugin)        │                            │
│  │                      │                            │
│  │ ├── NodeStageVolume  │  格式化 + 挂载到全局目录     │
│  │ ├── NodePublishVolume│  绑定挂载到 Pod 目录        │
│  │ ├── NodeUnpublish    │  从 Pod 目录卸载             │
│  │ └── NodeUnstage      │  从全局目录卸载              │
│  └──────────────────────┘                            │
│                                                       │
│  kube-controller-manager                             │
│    │                                                  │
│    │ gRPC                                             │
│    ▼                                                  │
│  ┌──────────────────────┐                            │
│  │ CSI Controller       │ ← 通常运行在控制平面        │
│  │ Driver               │                            │
│  │                      │                            │
│  │ ├── CreateVolume     │  创建存储卷                  │
│  │ ├── DeleteVolume     │  删除存储卷                  │
│  │ ├── ControllerPublish│  将卷附加到节点              │
│  │ ├── ControllerUnpub  │  将卷从节点分离              │
│  │ ├── CreateSnapshot   │  创建快照                   │
│  │ └── ListVolumes      │  列出所有卷                  │
│  └──────────────────────┘                            │
└───────────────────────────────────────────────────────┘

// Volume 生命周期：
// 1. Provision（供应）：PV 由 CSI Controller 动态创建
// 2. Attach（附加）：将存储卷附加到目标节点（云盘 attach）
// 3. Mount（挂载）：
//    a. StageVolume：格式化 → 挂载到全局目录 (/var/lib/kubelet/plugins/...)
//    b. PublishVolume：绑定挂载到 Pod 目录 (/var/lib/kubelet/pods/{uid}/volumes/...)
// 4. 使用：Pod 内部通过 volumeMounts 访问
// 5. 卸载：反向操作 Publish → Stage → Detach → Delete
```

---

## 十、etcd 与 K8s 的数据一致性保证

```
┌────────────────────────────────────────────────────────┐
│              资源对象的版本管理                           │
│                                                        │
│  每个资源对象有三个版本标识：                             │
│                                                        │
│  ① resourceVersion                                     │
│     ├── 由 etcd 提供（全局单调递增）                     │
│     ├── 每次修改都会变化                                 │
│     ├── 用于乐观并发控制（CAS）                          │
│     └── 用于 Watch 指定起始版本                          │
│                                                        │
│  ② generation                                          │
│     ├── 每次修改 spec 时 +1                             │
│     ├── 修改 metadata/annotations 不会变化              │
│     └── Controller 用于判断 spec 是否变更               │
│                                                        │
│  ③ observedGeneration                                  │
│     ├── Controller 更新 status 时写入                   │
│     ├── 表示 Controller 已处理到哪个 generation          │
│     └── 用于判断 Controller 是否跟上最新 spec           │
└────────────────────────────────────────────────────────┘

// 乐观并发控制示例（Update 操作）：
// 1. GET Pod → 获取 resourceVersion=12345
// 2. 修改 Pod spec
// 3. PUT Pod（携带 resourceVersion=12345）
// 4. API Server 检查：
//    如果 etcd 中的 resourceVersion == 12345 → 更新成功
//    如果不等 → 返回 409 Conflict → 客户端需要重新 GET 再更新
```

---

## 十一、关键数据结构与算法

| 组件 | 底层数据结构/算法 | 说明 |
|------|------------------|------|
| **etcd** | B+ Tree (bbolt) + Raft | 持久化存储 + 分布式共识 |
| **API Server WatchCache** | 环形缓冲区 (Ring Buffer) | 高效存储资源变更历史 |
| **Informer** | Delta FIFO Queue | 有序处理资源事件 |
| **Scheduler 优先队列** | 二叉堆 (Heap) | 按优先级出队 Pod |
| **iptables kube-proxy** | 链表遍历 | 规则链式匹配 O(n) |
| **IPVS kube-proxy** | 哈希表 | 虚拟服务查找 O(1) |
| **NetworkPolicy (Calico)** | 有序 iptables 规则 / eBPF Map | 网络策略匹配 |
| **etcd compaction** | MVCC (多版本并发控制) | 保留历史版本，定期压缩 |
| **EndpointSlice** | 分片列表 | 100 个一组，增量更新 |

---

以上是 Kubernetes 核心组件的底层机制解析。如果你想深入某个具体方向（如 eBPF 数据面、K8s 多集群联邦、自定义 Operator 开发原理等），可以继续追问。
