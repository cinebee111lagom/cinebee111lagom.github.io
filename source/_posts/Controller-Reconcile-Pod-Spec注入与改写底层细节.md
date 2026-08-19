---
title: Controller Reconcile 过程中 Pod Spec 注入与改写的底层细节
date: 2026-09-07 22:15:00
tags:
  - Kubernetes
  - Controller
  - Reconcile
  - Pod
categories:
  - Kubernetes
---

## 一、OwnerReference 的底层机制

### 1.1 数据结构

OwnerReference 是 Kubernetes API 对象的标准字段，定义在 `k8s.io/apimachinery/pkg/apis/meta/v1` 中：

```go
// k8s.io/apimachinery/pkg/apis/meta/v1/types.go

type OwnerReference struct {
    // API version of the referent
    APIVersion string `json:"apiVersion" protobuf:"bytes,5,opt,name=apiVersion"`
    
    // Kind of the referent
    Kind string `json:"kind" protobuf:"bytes,1,opt,name=kind"`
    
    // Name of the referent
    Name string `json:"name" protobuf:"bytes,3,opt,name=name"`
    
    // UID of the referent
    UID types.UID `json:"uid" protobuf:"bytes,4,opt,name=uid,opt,casttype=k8s.io/apimachinery/pkg/types.UID"`
    
    // If true, the referent is not shown in the owner's list
    // of dependents (后台删除时是否从 owner 的 dependents 列表中移除)
    // +optional
    BlockOwnerDeletion *bool `json:"blockOwnerDeletion,omitempty" protobuf:"varint,7,opt,name=blockOwnerDeletion"`
    
    // If true, the owner can only be garbage collected
    // when all dependents with this finalizer are gone
    // +optional
    Controller *bool `json:"controller,omitempty" protobuf:"varint,8,opt,name=controller"`
}
```

### 1.2 Training Operator 中的设置代码

在 `training-operator` 的源码中（以 PyTorchJob 为例），OwnerReference 的设置发生在 `pod.go` 中：

```go
// pkg/controller.v1/pytorch/pytorchjob_controller.go
// 或对应版本的 pod.go

func (r *PyTorchJobReconciler) createNewPod(
    job *kubeflowv1.PyTorchJob,
    podTemplate *corev1.PodTemplateSpec,
    replicaType kubeflowv1.ReplicaType,
    replicaIndex int,
) error {
    
    // 1. 构建 Pod Name
    podName := fmt.Sprintf("%s-%s-%d", job.Name, strings.ToLower(string(replicaType)), replicaIndex)
    
    // 2. 设置 OwnerReference
    isController := true
    blockOwnerDeletion := true
    ownerRef := metav1.OwnerReference{
        APIVersion:         kubeflowv1.SchemeGroupVersion.String(), // "kubeflow.org/v1"
        Kind:               "PyTorchJob",
        Name:               job.Name,
        UID:                job.UID,
        Controller:         &isController,
        BlockOwnerDeletion: &blockOwnerDeletion,
    }
    
    // 3. 将 OwnerRef 注入到 Pod 的 ObjectMeta 中
    podTemplate.ObjectMeta.OwnerReferences = []metav1.OwnerReference{ownerRef}
    
    // 4. 创建 Pod
    pod, err := r.KubeClientSet.CoreV1().Pods(job.Namespace).Create(
        context.TODO(),
        &corev1.Pod{
            ObjectMeta: podTemplate.ObjectMeta,
            Spec:       podTemplate.Spec,
        },
        metav1.CreateOptions{},
    )
    
    return err
}
```

### 1.3 OwnerReference 触发 Garbage Collection 的底层链路

```
用户删除 PyTorchJob (kubectl delete pytorchjob mnist)
       │
       ▼
API Server 收到 DELETE 请求
       │
       ▼
API Server 不立即删除，而是给 PyTorchJob 加上 DeletionTimestamp
  metadata:
    deletionTimestamp: "2024-01-15T10:30:00Z"
    finalizers: [kubeflow.org/clean-up]  ← Controller 需要处理的 finalizer
       │
       ▼
Garbage Collector Controller (KCM 内置) 检测到:
  - PyTorchJob 有 DeletionTimestamp
  - 找到所有 ownerReferences 指向该 UID 的对象
    → Worker-0 Pod (OwnerRef UID = PyTorchJob.UID)
    → Worker-1 Pod (OwnerRef UID = PyTorchJob.UID)
    → Worker-2 Pod (OwnerRef UID = PyTorchJob.UID)
    → Headless Service (OwnerRef UID = PyTorchJob.UID)
       │
       ▼
GC 对每个 dependent 对象执行:
  if ownerRef.BlockOwnerDeletion == true:
      → 向 owner 的 finalizer 列表中添加 "foregroundDeletion"
      → 先删除 dependents
      → 等所有 dependents 删除完毕
      → 移除 finalizer
      → 最终删除 owner
```

GC 的两种删除策略：

```
PropagationPolicy: "Foreground"  (前台删除)
  Owner (DeletionTimestamp 设置)
    → 所有 Dependents 被删除
      → Owner 被删除

PropagationPolicy: "Background"  (后台删除，默认)
  Owner 立即从 API Server 删除
    → GC Controller 异步扫描并删除 Dependents
    
PropagationPolicy: "Orphan"      (孤儿删除)
  Owner 被删除
    → OwnerReferences 被清除，Dependents 保留
```

### 1.4 BlockOwnerDeletion 的精确语义

```go
// 当 GC 决定删除一个 dependent 时:

func (gc *GarbageCollector) processItem(item *node) error {
    // 获取所有 ownerReferences
    for _, ownerRef := range item.ownerReferences {
        if *ownerRef.BlockOwnerDeletion {
            // 阻塞 owner 的删除，直到此 dependent 被成功删除
            // GC 会先处理这个 dependent，再处理 owner
            
            // 实际机制：在 owner 上添加 finalizer
            // finalizer name: "foregroundDeletion" 或自定义的
            owner.Finalizers = append(owner.Finalizers, orphanFinalizer)
        }
    }
}
```

**实际影响：** 当你执行 `kubectl delete pytorchjob mnist --cascade=foreground` 时，你会看到：

```
$ kubectl get pods
NAME                     STATUS        REASON
mnist-worker-0           Terminating   (正在被删除)
mnist-worker-1           Terminating   (正在被删除)
mnist-worker-2           Terminating   (正在被删除)

$ kubectl get pytorchjob mnist
NAME    STATUS     AGE
mnist   Deleting   5m    ← 等所有 Pod 删除完毕后才会消失
```

---

## 二、Label 注入的底层细节

### 2.1 Label 体系设计

Training Operator 注入的 Label 体系（以 kubeflow/training-operator v1.7+ 为例）：

```go
// pkg/controller.v1/common/job.go 或 util.go

const (
    // 标准 Label Keys
    LabelGroupName   = "kubeflow.org"              // group
    LabelJobName     = "kubeflow.org/job-name"     // 对应 CRD 的 metadata.name
    LabelReplicaType = "kubeflow.org/replica-type"  // "master", "worker", "ps"
    LabelReplicaIndex = "kubeflow.org/replica-index" // "0", "1", "2"
    LabelControllerName = "controller-revision-hash" // StatefulSet 的 ControllerRevision
)

// 注入过程
func GenLabels(jobName string) map[string]string {
    return map[string]string{
        LabelGroupName: "kubeflow.org",
        "app":          "pytorchjob",   // 或 tfjob, mpijob 等
        LabelJobName:   jobName,
    }
}

// 在创建 Pod 时进一步细化
func setReplicaLabels(labels map[string]string, replicaType string, index int) {
    labels[LabelReplicaType] = strings.ToLower(string(replicaType))
    labels[LabelReplicaIndex] = strconv.Itoa(index)
}
```

### 2.2 Label 在 Controller 中的实际用途

Controller 使用 Label Selector 来 **发现和管理** 已存在的 Pod，而不是维护一个内部映射表：

```go
// pkg/controller.v1/common/job.go

func (jc *JobController) GetPodsForJob(
    job metav1.Object,
) ([]*corev1.Pod, error) {
    
    // 构建 Label Selector
    selector, err := metav1.LabelSelectorAsSelector(&metav1.LabelSelector{
        MatchLabels: map[string]string{
            LabelGroupName: "kubeflow.org",
            LabelJobName:   job.GetName(),
        },
    })
    
    // 用 Selector 从 Informer 缓存中过滤
    pods, err := jc.PodLister.Pods(job.GetNamespace()).List(selector)
    
    return pods, err
}
```

**为什么用 Label Selector 而不是 OwnerReference 链查？**

```
两种方式的对比:

方式 1: OwnerReference 链查
  - 需要遍历所有 Pod，检查 OwnerReferences 是否匹配
  - O(n) 时间复杂度，n = 集群中所有 Pod 数量
  - API Server 压力大

方式 2: Label Selector (Kubeflow 的实际做法)
  - Informer 内部维护了 Label 索引
  - Selector 匹配是 O(1) 索引查找
  - 不访问 API Server，直接从本地缓存读取
  - 性能远优于 OwnerReference 链查
```

### 2.3 Label 在 Headless Service Selector 中的作用

Label 同时被 Headless Service 的 Selector 引用，建立 DNS → Pod 的映射：

```
Headless Service Selector:
  kubeflow.org/job-name: mnist-training
  kubeflow.org/replica-type: worker

Pod Labels:
  kubeflow.org/job-name: mnist-training    ← 匹配
  kubeflow.org/replica-type: worker         ← 匹配
  kubeflow.org/replica-index: "0"

结论: 该 Pod 属于此 Service 的 Endpoints
  → DNS A 记录: mnist-training-worker-0.mnist-training-worker → Pod IP
```

### 2.4 Controller 如何使用 Label 管理 Replica 的精确匹配

```go
// 当 Controller 需要判断 "Worker-2 是否存在" 时：

func (jc *JobController) getPodForReplica(
    pods []*corev1.Pod,
    replicaType string,
    index int,
) *corev1.Pod {
    
    for _, pod := range pods {
        rt := pod.Labels[LabelReplicaType]
        ri := pod.Labels[LabelReplicaIndex]
        
        if rt == replicaType && ri == strconv.Itoa(index) {
            return pod
        }
    }
    return nil // 不存在，需要创建
}
```

这在 Reconcile 循环中至关重要——Controller 不维护任何内存中的状态，**每次都通过 Label Selector 从 Informer 缓存中重新查询**，这是 Kubernetes Operator 的标准范式，保证了 Controller 的无状态性和可恢复性。

---

## 三、Headless Service 创建的底层细节

### 3.1 Controller 中的创建代码

```go
// pkg/controller.v1/pytorch/service.go

func (r *PyTorchJobReconciler) createNewService(
    job *kubeflowv1.PyTorchJob,
    podTemplate *corev1.PodTemplateSpec,
    replicaType kubeflowv1.ReplicaType,
) (*corev1.Service, error) {
    
    serviceName := fmt.Sprintf("%s-%s", job.Name, strings.ToLower(string(replicaType)))
    
    // 标准 Service 的 port 是从 container 的 ports 中提取的
    ports := extractServicePorts(podTemplate)
    
    // 仅当用户没有设置 servicePort 时使用默认端口
    if len(ports) == 0 {
        ports = append(ports, corev1.ServicePort{
            Name:       "training-port",
            Port:       23456,              // 默认训练通信端口
            TargetPort: intstr.FromInt(23456),
            Protocol:   corev1.ProtocolTCP,
        })
    }
    
    service := &corev1.Service{
        ObjectMeta: metav1.ObjectMeta{
            Name:      serviceName,
            Namespace: job.Namespace,
            OwnerReferences: []metav1.OwnerReference{
                *metav1.NewControllerRef(job, kubeflowv1.SchemeGroupVersion.WithKind("PyTorchJob")),
            },
            Labels: map[string]string{
                LabelGroupName: "kubeflow.org",
                LabelJobName:   job.Name,
            },
        },
        Spec: corev1.ServiceSpec{
            ClusterIP: "None",   // ★ Headless！关键字段
            Selector: map[string]string{
                LabelGroupName:   "kubeflow.org",
                LabelJobName:     job.Name,
                LabelReplicaType: strings.ToLower(string(replicaType)),
            },
            PublishNotReadyAddresses: true,  // ★ 关键！见下文详解
            Ports: ports,
        },
    }
    
    return r.KubeClientSet.CoreV1().Services(job.Namespace).Create(
        context.TODO(), service, metav1.CreateOptions{},
    )
}
```

### 3.2 ClusterIP: "None" 的底层语义

当 `ClusterIP` 设置为 `"None"` 时，kube-proxy **不为此 Service 创建任何 iptables/ipvs 规则**：

```
普通 Service (ClusterIP: "10.96.0.100"):
  - kube-proxy 创建 DNAT 规则:
    -A KUBE-SERVICES -d 10.96.0.100/32 -p tcp --dport 23456 \
      -j KUBE-SVC-XXXXX
    -A KUBE-SVC-XXXXX -j KUBE-SEP-AAA   (33% 概率)
    -A KUBE-SVC-XXXXX -j KUBE-SEP-BBB   (33% 概率)
    -A KUBE-SVC-XXXXX -j KUBE-SEP-CCC   (33% 概率)
  - 所有流量先到 ClusterIP，再随机分发到某个 Pod
  - 额外一跳网络延迟，且无法保证到达哪个 Pod

Headless Service (ClusterIP: "None"):
  - kube-proxy 什么都不做
  - CoreDNS 直接返回后端 Pod 的 IP 列表:
    ;; ANSWER SECTION:
    mnist-training-worker.default.svc.cluster.local. 5 IN A 10.244.1.5
    mnist-training-worker.default.svc.cluster.local. 5 IN A 10.244.2.8
    mnist-training-worker.default.svc.cluster.local. 5 IN A 10.244.3.12
    
  - 对于 StatefulSet 模式（有 Pod 序号），还有:
    mnist-training-worker-0.default.svc.cluster.local. 5 IN A 10.244.1.5
    mnist-training-worker-1.default.svc.cluster.local. 5 IN A 10.244.2.8
    mnist-training-worker-2.default.svc.cluster.local. 5 IN A 10.244.3.12
```

### 3.3 PublishNotReadyAddresses: true 的关键意义

```go
PublishNotReadyAddresses: true,  // ★ 很容易被忽略
```

这个字段的底层含义：

```
场景：Pod 处于 ContainerCreating 状态（尚未 Ready）

PublishNotReadyAddresses: false (默认):
  - CoreDNS 只返回 Ready 的 Pod IP
  - 如果 Worker-0 先启动，Worker-1 还在拉镜像
  - Worker-0 查询 DNS: 只得到自己的 IP
  - init_process_group() 永远等不到其他 Worker
  → 死锁！

PublishNotReadyAddresses: true:
  - CoreDNS 返回所有 Pod IP，不论 Ready 与否
  - Worker-0 查询 DNS: 得到所有 3 个 Worker 的 IP
  - Worker-0 的 init_process_group() 在 TCPStore 上等待
  - Worker-1 启动后加入 → 握手成功
  - Worker-2 启动后加入 → 握手成功
  → 全员就绪，开始训练
```

这背后的 CoreDNS 实现：

```go
// kubernetes/dns/svc.go (简化)
func (k *Kubernetes) Records(...) {
    svc := getService(name)
    
    if svc.Spec.ClusterIP == v1.ClusterIPNone {
        // Headless: 返回 Endpoints 中的 Pod IPs
        endpoints := getEndpoints(svc)
        
        for _, ep := range endpoints {
            if svc.Spec.PublishNotReadyAddresses {
                // 不过滤，全部返回
                records = append(records, ep.Address)
            } else {
                // 只返回 Ready 的
                if ep.Conditions.Ready == true {
                    records = append(records, ep.Address)
                }
            }
        }
    }
}
```

### 3.4 Headless Service 与 Endpoint Controller 的交互

```
API Server 中 Service 创建
       │
       ▼
EndpointSlice Controller (在 kube-controller-manager 中) Watch 到新 Service
       │
       ▼
扫描 Service.Spec.Selector 匹配的 Pod
       │
       ▼
创建 EndpointSlice:
  apiVersion: discovery.k8s.io/v1
  kind: EndpointSlice
  metadata:
    name: mnist-training-worker-abc12
    labels:
      kubernetes.io/service-name: mnist-training-worker
  endpoints:
    - addresses: ["10.244.1.5"]
      conditions:
        ready: false          ← Pod 还在创建中
      targetRef:
        kind: Pod
        name: mnist-training-worker-0
    - addresses: ["10.244.2.8"]
      conditions:
        ready: true           ← Pod 已就绪
      targetRef:
        kind: Pod
        name: mnist-training-worker-1
  ports:
    - name: training-port
      port: 23456
       │
       ▼
CoreDNS Watch EndpointSlice 变更
       │
       ▼
更新内部 DNS 记录:
  if service.PublishNotReadyAddresses:
      addAll(endpoints)       ← 包括 ready=false 的
  else:
      addOnly(ready=true)
```

---

## 四、环境变量注入的精确代码路径

### 4.1 PyTorchJob 的环境变量注入

```go
// pkg/controller.v1/pytorch/pod.go

func setPodEnv(
    job *kubeflowv1.PyTorchJob,
    podTemplateSpec *corev1.PodTemplateSpec,
    replicaType kubeflowv1.ReplicaType,
    replicaIndex int,
) error {
    
    // 获取 Master 的 Pod Name
    masterName := job.ControllerName() + "-master-0"
    
    // 获取 Master Service Name
    masterAddr := job.Name + "-master"   // Headless Service FQDN
    
    // 查找用户是否在 container 的 env 中已经自定义了这些变量
    // 如果已自定义，不覆盖
    existingEnv := make(map[string]bool)
    for _, env := range podTemplateSpec.Spec.Containers[0].Env {
        existingEnv[env.Name] = true
    }
    
    // 注入 PyTorch 分布式训练所需的环境变量
    envVars := []corev1.EnvVar{
        {
            Name:  "MASTER_ADDR",
            Value: masterAddr,
        },
        {
            Name:  "MASTER_PORT",
            Value: "23456",
        },
        {
            // WORLD_SIZE 的计算:
            // = sum(每个 replicaType 的 replicas * nprocPerNode)
            Name:  "WORLD_SIZE",
            Value: strconv.Itoa(calcWorldSize(job)),
        },
        {
            // RANK 的计算:
            // Worker-0 → rank 0
            // Worker-1 → rank 1
            // Master-0 → rank (如果 master 也参与训练)
            Name:  "RANK",
            Value: strconv.Itoa(calcRank(replicaType, replicaIndex, job)),
        },
    }
    
    // 只注入用户没有手动设置的变量
    for _, env := range envVars {
        if !existingEnv[env.Name] {
            podTemplateSpec.Spec.Containers[0].Env = append(
                podTemplateSpec.Spec.Containers[0].Env,
                env,
            )
        }
    }
    
    return nil
}
```

### 4.2 WORLD_SIZE 和 RANK 的精确计算逻辑

```go
// pkg/controller.v1/common/util.go

func calcWorldSize(job *kubeflowv1.PyTorchJob) int {
    worldSize := 0
    
    for rtype, spec := range job.Spec.PyTorchReplicaSpecs {
        replicas := int(*spec.Replicas)
        
        // nprocPerNode: 每个 Pod 中启动几个进程
        // PyTorchJob 特有字段
        nprocPerNode := 1
        if job.Spec.NprocPerNode != nil {
            nprocPerNode, _ = strconv.Atoi(*job.Spec.NprocPerNode)
        }
        
        worldSize += replicas * nprocPerNode
    }
    
    return worldSize
}

// 示例:
// PyTorchJob:
//   Master: replicas=1
//   Worker: replicas=3
//   NprocPerNode: "4"
//
// WORLD_SIZE = (1 + 3) × 4 = 16
//
// RANK 计算:
//   Master-0: rank 0~3  (4 个进程, rank = 0*nproc+local_rank)
//   Worker-0: rank 4~7
//   Worker-1: rank 8~11
//   Worker-2: rank 12~15
```

### 4.3 MPIJob 的环境变量注入（差异较大）

MPIJob 的环境变量注入方式与 PyTorchJob 不同，因为 MPI 通过 `mpirun` 的参数而非环境变量传递 rank 信息：

```go
// pkg/controller.v1/mpi/pod.go

func (jc *MPIJobController) setPodEnv(
    job *kubeflowv1.MPIJob,
    podTemplateSpec *corev1.PodTemplateSpec,
    replicaType kubeflowv1.ReplicaType,
    replicaIndex int,
) {
    // MPI 的环境变量注入在 Launcher Pod 中通过命令行完成
    // Worker Pod 主要注入:
    //   - OMPI_MCA_*=* (OpenMPI 参数)
    //   - LD_PRELOAD (可能需要的 libnccl 等)
    
    if replicaType == kubeflowv1.MPIJobReplicaTypeLauncher {
        // Launcher 特有的环境变量
        envVars := []corev1.EnvVar{
            {
                Name:  "OMPI_MCA_orte_default_hostfile",
                Value: "/etc/mpi/hostfile",  // Controller 生成的 hostfile
            },
        }
    }
    
    // 共同的 NCCL 相关环境变量
    commonEnvVars := []corev1.EnvVar{
        {Name: "NCCL_DEBUG", Value: "INFO"},
        {Name: "NCCL_SOCKET_IFNAME", Value: "eth0"},
    }
}
```

---

## 五、Pod Spec 的更深层改写

### 5.1 Command 和 Args 的改写

Controller 有时会改写容器的启动命令，特别是在使用 `torchrun` 时：

```go
// 注入 torchrun 作为启动器（可选，取决于框架版本）

// 旧方式: torch.distributed.launch
// Controller 不改写 Command，用户自己在 YAML 中写
// command: ["python", "-m", "torch.distributed.launch", "train.py"]

// 新方式 (PyTorch 2.0+): torchrun
// Controller 可能自动注入:
func injectTorchRun(
    podSpec *corev1.PodSpec,
    nprocPerNode string,
    nnodes int,
    nodeRank int,
) {
    originalCmd := podSpec.Containers[0].Command
    originalArgs := podSpec.Containers[0].Args
    
    // 构建 torchrun 命令
    torchRunArgs := []string{
        "--nproc_per_node=" + nprocPerNode,
        "--nnodes=" + strconv.Itoa(nnodes),
        "--node_rank=" + strconv.Itoa(nodeRank),
        "--master_addr=$(MASTER_ADDR)",
        "--master_port=$(MASTER_PORT)",
    }
    
    // 合并用户原始命令
    podSpec.Containers[0].Command = []string{"torchrun"}
    podSpec.Containers[0].Args = append(torchRunArgs, originalCmd...)
    podSpec.Containers[0].Args = append(podSpec.Containers[0].Args, originalArgs...)
}
```

### 5.2 SecurityContext 的注入

```go
// 某些训练场景需要特殊权限

func injectSecurityContext(podSpec *corev1.PodSpec) {
    // RDMA 训练可能需要 IPC_LOCK 权限（注册大页内存）
    podSpec.Containers[0].SecurityContext = &corev1.SecurityContext{
        Capabilities: &corev1.Capabilities{
            Add: []corev1.Capability{
                "IPC_LOCK",    // 锁定内存，防止被 swap
                "SYS_RESOURCE", // 提高 rlimit（某些 RDMA 驱动需要）
            },
        },
    }
    
    // 某些场景还需要 HostPID（CUDA MPS 需要）
    // podSpec.HostPID = true
    
    // 或者需要共享内存（PyTorch DataLoader num_workers>0 时）
    // 在 volumeMounts 中挂载 /dev/shm
    podSpec.Containers[0].VolumeMounts = append(
        podSpec.Containers[0].VolumeMounts,
        corev1.VolumeMount{
            Name:      "dshm",
            MountPath: "/dev/shm",
        },
    )
    podSpec.Volumes = append(podSpec.Volumes, corev1.Volume{
        Name: "dshm",
        VolumeSource: corev1.VolumeSource{
            EmptyDir: &corev1.EmptyDirVolumeSource{
                Medium: corev1.StorageMediumMemory, // 使用 tmpfs (RAM)
            },
        },
    })
}
```

### 5.3 /dev/shm 的底层意义

```
问题：为什么 /dev/shm 需要单独配置？

默认 Docker/K8s 中 /dev/shm 大小为 64MB:
  $ df -h /dev/shm
  Filesystem      Size  Used Avail Use% Mounted on
  shm              64M   0   64M   0%  /dev/shm

PyTorch DataLoader (num_workers > 0):
  - 使用 Python multiprocessing.shared_memory
  - 在 /dev/shm 中创建共享内存段
  - 多个 worker 进程共享 tensor 数据
  - 如果 /dev/shm < 训练数据的共享大小 → OOM crash

解决方案:
  EmptyDir.medium = "Memory" → 挂载 tmpfs，大小默认 = 节点内存的 50%
  或通过 --shm-size 参数指定大小
```

### 5.4 Pod Overhead（Runtime Overhead）的影响

Kubernetes 1.18+ 引入 Pod Overhead：

```yaml
# RuntimeClass 定义
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia-container
handler: nvidia
overhead:
  podFixed:
    memory: "256Mi"     # 容器运行时的固定内存开销
    cpu: "250m"         # 容器运行时的固定 CPU 开销
```

当 Controller 创建 Pod 时，如果指定了 RuntimeClass，kubelet 的 Admission 过程会自动加上 Overhead：

```
用户请求:  cpu=16, memory=64Gi, gpu=4
Runtime Overhead: cpu=250m, memory=256Mi
实际节点需求: cpu=16.25, memory=64.25Gi

如果节点剩余资源 < 实际需求 → Pod Pending
```

---

## 六、完整 Reconcile 循环的源码级流程

```
Reconcile(ctx, request) 
│
├── 1. Get PyTorchJob from API Server
│   r.Get(ctx, req.NamespacedName, pytorchjob)
│
├── 2. 检查是否需要 finalize（处理删除）
│   if pytorchjob.DeletionTimestamp != nil:
│       → 执行 cleanup finalizer
│       → 清理外部资源（如 TensorBoard、Prometheus 规则等）
│       → 移除 finalizer
│       → return
│
├── 3. 添加 finalizer（如果还没有）
│   if !hasFinalizer(pytorchjob):
│       pytorchjob.Finalizers = append(pytorchjob.Finalizers, "kubeflow.org/clean-up")
│       r.Update(ctx, pytorchjob)
│       return  ← 重新进入 Reconcile
│
├── 4. 判断 Job 是否已经终态
│   if pytorchjob.Status.Phase in (Succeeded, Failed):
│       return  ← 不再处理
│
├── 5. 获取当前所有相关 Pod（通过 Label Selector）
│   pods, _ := r.getPodsForJob(pytorchjob)
│   // Selector: {kubeflow.org/job-name: "mnist", kubeflow.org/group-name: "kubeflow.org"}
│
├── 6. 对每个 ReplicaType (Master, Worker, PS) 执行 reconcile:
│   │
│   for replicaType, replicaSpec := range pytorchjob.Spec.PyTorchReplicaSpecs {
│       │
│       ├── 6a. 检查 replicas 数量
│       │   desiredReplicas = *replicaSpec.Replicas
│       │   actualReplicas = countPods(pods, replicaType)
│       │
│       ├── 6b. 如果 actual < desired → 创建新 Pod
│       │   for i := actualReplicas; i < desiredReplicas; i++ {
│       │       // 注入 OwnerReference
│       │       // 注入 Labels
│       │       // 注入 ENV vars (MASTER_ADDR, WORLD_SIZE, RANK...)
│       │       // 注入 SecurityContext
│       │       // 注入 Volume (/dev/shm, checkpoint PVC)
│       │       // 创建 Pod
│       │       // 同时确保 Headless Service 存在
│       │       r.createNewPod(pytorchjob, podTemplate, replicaType, i)
│       │   }
│       │
│       ├── 6c. 如果 actual > desired → 删除多余 Pod
│       │   for _, excessPod := range excessPods {
│       │       // 优先删除 index 最大的
│       │       r.KubeClientSet.CoreV1().Pods(ns).Delete(ctx, excessPod.Name, ...)
│       │   }
│       │
│       └── 6d. 统计各 Pod 的状态
│           running := 0; succeeded := 0; failed := 0; pending := 0
│           for _, pod := range pods {
│               switch pod.Status.Phase {
│               case Running:   running++
│               case Succeeded: succeeded++
│               case Failed:    failed++
│               case Pending:   pending++
│               }
│           }
│   }
│
├── 7. 确定整体 Job 状态
│   │
│   ├── 所有 Replica 的所有 Pod 都 Succeeded → JobPhase = Succeeded
│   ├── 任何 Pod Failed + 超过重试限制 → JobPhase = Failed
│   ├── 任何 Pod Running → JobPhase = Running
│   └── 否则 → JobPhase = Restarting / Pending
│
├── 8. 更新 PyTorchJob Status
│   pytorchjob.Status = kubeflowv1.JobStatus{
│       Conditions:    conditions,
│       ReplicaStatuses: replicaStatuses,
│       StartTime:     startTime,
│       CompletionTime: completionTime,
│   }
│   r.Status().Update(ctx, pytorchjob)
│
└── 9. 返回 Requeue 结果
    if job is still running:
        return ctrl.Result{RequeueAfter: 10 * time.Second}  ← 定期检查
    else:
        return ctrl.Result{}  ← 终态，不再 Requeue
```

---

## 七、Informer 与缓存层的底层细节

Controller 不直接调用 API Server 的 List/Watch，而是通过 **Informer 机制**：

```
┌─────────────────────────────────────────────────────────────┐
│                    Training Operator Pod                      │
│                                                              │
│  ┌────────────────┐     ┌──────────────────┐                │
│  │  Controller     │     │  Controller       │               │
│  │  (PyTorchJob)   │     │  (TFJob)          │               │
│  └───────┬────────┘     └────────┬─────────┘                │
│          │                       │                           │
│          ▼                       ▼                           │
│  ┌──────────────────────────────────────────────┐           │
│  │           Shared Informer Factory              │           │
│  │                                                │           │
│  │  ┌─────────────────┐  ┌─────────────────────┐│           │
│  │  │ PodInformer      │  │ PyTorchJobInformer   ││           │
│  │  │                  │  │                      ││           │
│  │  │ Reflector        │  │ Reflector            ││           │
│  │  │   ↓ (List/Watch) │  │   ↓ (List/Watch)     ││           │
│  │  │ Delta FIFO       │  │ Delta FIFO           ││           │
│  │  │   ↓              │  │   ↓                  ││           │
│  │  │ Indexer (cache)  │  │ Indexer (cache)      ││           │
│  │  │ + Label Index    │  │ + Name Index         ││           │
│  │  └─────────────────┘  └─────────────────────┘│           │
│  └──────────────────────────────────────────────┘           │
│          │                           │                       │
│          ▼                           ▼                       │
│   SharedInformerFactory.Start(ctx)                           │
│          │                                                   │
│          ▼                                                   │
│   goroutine: Reflector.List() → 连接 API Server              │
│   goroutine: Reflector.Watch() → 持续 Watch streaming        │
└─────────────────────────────────────────────────────────────┘
         │                    │
         │ List/Watch         │ List/Watch
         ▼                    ▼
    ┌──────────────────────────────┐
    │      Kubernetes API Server    │
    │  (etcd ← 持久化存储)          │
    └──────────────────────────────┘
```

### Informer 的关键数据结构

```go
// k8s.io/client-go/tools/cache/reflector.go

type Reflector struct {
    name          string
    listWatcher   ListerWatcher  // 封装了 List 和 Watch 的 gRPC 调用
    lastSyncResourceVersion string
    
    // 存储
    store         Store          // 本地缓存（ThreadSafe Store）
    listerCh      chan time.Time  // 触发 Relist 的信号
}

func (r *Reflector) ListAndWatch(stopCh <-chan struct{}) error {
    // 1. 初始 List
    list, err := r.listerWatcher.List(metav1.ListOptions{
        ResourceVersion: "0",  // 从头开始
    })
    
    // 将所有对象放入 Store
    r.syncWith(items, resourceVersion)
    
    // 2. 持续 Watch
    for {
        watch, err := r.listerWatcher.Watch(metav1.ListOptions{
            ResourceVersion: resourceVersion,
            Watch:           true,
        })
        
        // 处理事件
        for event := range watch.ResultChan() {
            switch event.Type {
            case Added:
                r.store.Add(event.Object)
            case Modified:
                r.store.Update(event.Object)
            case Deleted:
                r.store.Delete(event.Object)
            case Bookmark:
                // 更新 ResourceVersion
            case Error:
                // 重新 List + Watch
            }
        }
    }
}
```

### Controller 通过 Informer 查询 Pod 的精确路径

```go
// Controller.reconcile() 中:
pods, err := r.PodLister.Pods(namespace).List(selector)

// 这个调用的完整路径:
// 1. PodLister.Pods(namespace) → 返回 namespacedPodLister
// 2. namespacedPodLister.List(selector) →
//    → 调用 indexer.ByIndex("label", ...)  (如果有 label index)
//    → 或遍历 index 中所有该 namespace 的 Pod
//    → 对每个 Pod 执行 selector.Matches(labels)
//    → 返回匹配的 Pod 列表（指针，不复制对象）

// ★ 关键：这里读的是 Informer 的本地缓存，不访问 API Server
// ★ 返回的是对象指针，修改会影响缓存（所以要 DeepCopy）
```

---

## 八、Reconcile 的并发控制与冲突处理

### 8.1 Controller 的并发模型

```go
// training-operator 的 main.go

func main() {
    mgr, _ := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
        // Controller 并发数配置
    })
    
    // PyTorchJob Controller 注册
    reconciler := &PyTorchJobReconciler{
        Client:    mgr.GetClient(),
        Scheme:    mgr.GetScheme(),
        Recorder:  mgr.GetEventRecorderFor("pytorchjob-controller"),
    }
    
    ctrl.NewControllerManagedBy(mgr).
        For(&kubeflowv1.PyTorchJob{}).             // Watch PyTorchJob CRD
        Owns(&corev1.Pod{}).                       // Watch owned Pods
        Owns(&corev1.Service{}).                   // Watch owned Services
        Complete(reconciler)
}

// controller-runtime 的默认行为:
// - 1 个 Worker goroutine per controller（可通过 MaxConcurrentReconciles 调整）
// - WorkQueue 使用 rate limiting（指数退避）
// - 同一个 key 不会并发处理（但不同 key 会）
```

### 8.2 Resource Version 冲突处理

```go
// 当 Controller 尝试更新 PyTorchJob Status 时:
err := r.Status().Update(ctx, pytorchjob)

// 如果在 reconcile 期间，另一个请求修改了 pytorchjob:
// → API Server 返回 HTTP 409 Conflict
// → controller-runtime 将该 key 重新加入 WorkQueue
// → 等待下一轮 Reconcile 重新读取最新状态

// 内部实现:
func (e *enqueueRequestForObject) Update(evt event.UpdateEvent, q workqueue.RateLimitingInterface) {
    // 两个 Object 都会触发 reconcile:
    // 1. evt.ObjectOld (旧版本)
    // 2. evt.ObjectNew (新版本)
    // controller-runtime 合并为一个 key，加入队列
    q.Add(reconcile.Request{NamespacedName: types.NamespacedName{
        Name:      evt.ObjectNew.GetName(),
        Namespace: evt.ObjectNew.GetNamespace(),
    }})
}
```

### 8.3 Rate Limiting 策略

```go
// controller-runtime 默认的 RateLimiter:
// ItemExponentialFailureRateLimiter + BucketRateLimiter

type ItemExponentialFailureRateLimiter struct {
    baseDelay  time.Duration  // 默认 5ms
    maxDelay   time.Duration  // 默认 1000s
}

// 第 1 次失败: 等 5ms
// 第 2 次失败: 等 10ms
// 第 3 次失败: 等 20ms
// ...
// 第 n 次失败: 等 min(5ms × 2^n, 1000s)

// BucketRateLimiter: 全局限速，每秒 10 个请求
// 两者取最大值作为最终等待时间
```

---

## 九、状态持久化的时序保证

```
关键问题：Controller 先创建 Pod 还是先更新 Status？

答案：先创建 Pod，再更新 Status

时序:
1. Reconcile 开始 → 读取 PyTorchJob（RV=100）
2. 决定创建 3 个 Worker Pod
3. 调用 API Server 创建 Pod-0 (成功)
4. 调用 API Server 创建 Pod-1 (成功)
5. 调用 API Server 创建 Pod-2 (网络超时，创建失败)
6. Reconcile 返回 Error → 加入 RateLimitedQueue

7. 下一轮 Reconcile → 重新读取 PyTorchJob（可能还是 RV=100）
8. 通过 Label Selector 查询 Pod → 找到 Pod-0 和 Pod-1
9. 发现需要 3 个但只有 2 个 → 创建 Pod-2
10. 成功 → 更新 PyTorchJob Status

这就是为什么 Reconcile 必须是 幂等的:
- 即使中间任何步骤失败，重试后都能得到正确结果
- 不依赖内存状态，全靠从 API Server/Informer 重新查询
- 创建已经存在的 Pod 会返回 AlreadyExists 错误 → 安全处理
```

---

## 十、总结：一层层的抽象叠加

```
用户写的 YAML (30 行)
       │
       ▼
API Server 存储 + 校验
       │
       ▼
Informer Watch → 本地缓存
       │
       ▼
Reconcile Loop
  ├── Label 查询当前 Pod 状态
  ├── 对比期望 vs 实际
  ├── 计算需要创建/删除的 Pod
  └── 执行补偿操作
       │
       ▼
Pod Spec 构建（约 200+ 行的注入逻辑）
  ├── OwnerReference  → GC 级联删除
  ├── Labels          → 索引查询 + Service Selector
  ├── ENV Vars        → 分布式训练 rendezvous
  ├── SecurityContext → GPU/RDMA 权限
  ├── Volumes         → /dev/shm + checkpoint PVC
  └── Annotations     → 调度器提示
       │
       ▼
API Server 创建 Pod
       │
       ▼
Scheduler 评分 + 绑定（含 Volcano Gang Scheduling）
       │
       ▼
kubelet 收到 Pod
  ├── Device Plugin Allocate (GPU + RDMA)
  ├── Topology Manager NUMA 校验
  ├── CNI 网络配置
  └── 容器创建
       │
       ▼
训练进程启动 → NCCL rendezvous → 训练
```

每一层都在为上一层隐藏复杂性，但每一层的 **失败模式** 也会影响上一层。理解这些底层细节，是诊断训练任务 Pending / Crash / 性能低下的关键。
