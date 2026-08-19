---
title: Pod Exit Code 底层细节
date: 2026-09-07 21:15:00
tags:
  - Kubernetes
  - Pod
  - Exit Code
  - 容器
categories:
  - Kubernetes
---

## 一、Exit Code 的本质

Exit Code 是**操作系统层面**的概念，不是 Kubernetes 发明的。它源于 Linux `waitpid()` 系统调用，是容器内 PID 1 进程终止时向父进程报告的 8-bit 整数（0-255）。

```
Linux 内核
    │
    │ waitpid(pid, &status, 0)
    │
    ▼
┌─────────────────────────────────────────┐
│  exit code = WEXITSTATUS(status)        │
│  取值范围: 0 ~ 255                       │
│                                          │
│  0   → 正常退出                          │
│  1-125 → 应用自定义错误                   │
│  126 → 命令无法执行（权限问题）            │
│  127 → 命令未找到                        │
│  128+ → 被信号杀死 (128 + signal_number) │
│  137 → SIGKILL (128+9)                   │
│  143 → SIGTERM (128+15)                  │
│  255 → 超出范围，通常为 -1 的无符号表示    │
└─────────────────────────────────────────┘
```



## 二、完整的退出码捕获链路

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                         Linux Kernel                              │
│                                                                   │
│  进程退出 → do_exit() → notify_parent() → SIGCHLD to parent      │
│                                                                   │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Container Runtime                               │
│                   (containerd / CRI-O)                             │
│                                                                   │
│  ┌─────────────────┐                                              │
│  │ containerd-shim  │  ← 每个容器一个 shim 进程                    │
│  │  wait(pid)       │  ← 调用 waitpid() 捕获 exit code            │
│  └────────┬─────────┘                                              │
│           │                                                        │
│           ▼                                                        │
│  ┌─────────────────────────────────────┐                          │
│  │  Container Status                   │                          │
│  │  {                                  │                          │
│  │    "exitCode": 137,                 │                          │
│  │    "reason": "OOMKilled",           │  ← 根据 OOM 判断         │
│  │    "finishedAt": "2025-03-15T..."   │                          │
│  │  }                                  │                          │
│  └────────┬────────────────────────────┘                          │
│           │                                                        │
└───────────┼──────────────────────────────────────────────────────┘
            │
            │  CRI gRPC: ContainerStatus()
            ▼
┌──────────────────────────────────────────────────────────────────┐
│                        kubelet                                     │
│                                                                   │
│  ┌──────────────────────────┐                                     │
│  │ kuberuntime_manager.go   │                                     │
│  │ convertToKubeContainer   │                                     │
│  │ Status()                 │                                     │
│  └────────────┬─────────────┘                                     │
│               │                                                    │
│               ▼                                                    │
│  ┌──────────────────────────┐                                     │
│  │ Pod Status 构建           │                                     │
│  │ ContainerStateTerminated │                                     │
│  │   ExitCode: 137          │                                     │
│  │   Reason: "OOMKilled"    │                                     │
│  └────────────┬─────────────┘                                     │
│               │                                                    │
│               ▼                                                    │
│  ┌──────────────────────────┐                                     │
│  │ statusManager            │                                     │
│  │ → PATCH Pod Status       │                                     │
│  │ → API Server              │                                     │
│  └──────────────────────────┘                                     │
└──────────────────────────────────────────────────────────────────┘
```



## 三、containerd 层的实现细节

### 3.1 shim 进程如何捕获退出码

```go
// containerd/runtime/v2/runc/container.go (简化)
// shim 进程通过 runc 启动容器，runc 创建真正的容器进程

// 1. runc 创建容器时，PID 1 的父进程是 shim
shim (pid=1000)
  └── container-pid-1 (pid=1001)

// 2. 当容器进程退出时，shim 调用 waitpid()
// containerd/cmd/containerd-shim-runc-v2/process/init.go
func (p *Init) Wait(ctx context.Context) (*Exit, error) {
    for {
        var status unix.WaitStatus
        pid, err := unix.Wait4(int(p.pid), &status, 0, nil)
        // ↑ 核心：阻塞等待子进程退出
        
        exitCode := status.ExitStatus()  // WEXITSTATUS
        exitStatus := uint32(exitCode)
        
        return &Exit{
            Pid:       pid,
            Status:    exitStatus,  // ← 这就是 exit code
            Timestamp: time.Now(),
        }, nil
    }
}
```

### 3.2 判断 OOMKilled 的机制

```go
// containerd/pkg/cri/server/container_status.go (简化)
func (c *criService) ContainerStatus(
    ctx context.Context, 
    r *runtime.ContainerStatusRequest,
) (*runtime.ContainerStatusResponse, error) {
    
    status := container.Status
    info, _ := container.Container.Info(ctx)
    
    // 判断是否 OOMKilled
    // 方法1: 从 runc 的 exit 文件读取
    // 方法2: 检查 cgroup memory.events
    // 方法3: 检查 status 中是否包含 "oom-killed" 标记
    
    if info.OOMKilled {
        resp.Status.Reason = "OOMKilled"
    }
    // exit code 137 本身不一定是 OOM！
    // 只有 runtime 明确检测到 OOM 才会设置 OOMKilled=true
}
```

**关键认知**：`exit code 137` ≠ 一定是 OOM。只有 exit code 137 **且** runtime 检测到 OOM 事件时，才会标记为 OOMKilled。

### 3.3 cgroup 中的 OOM 检测

```
/sys/fs/cgroup/memory/kubepods/burstable/pod{uid}/{container_id}/
├── memory.oom_control
│   └── oom_kill_disable 0
│   └── under_oom 0
│   └── oom_kill 1        ← 被 OOM killer 杀死的次数
│
├── memory.events
│   └── oom 1             ← OOM 发生次数
│   └── oom_kill 1        ← 实际被 kill 的次数
│
└── memory.peak           ← 峰值内存
```

containerd shim 在容器退出后读取这些文件来判断是否发生了 OOM。

## 四、CRI 接口层

### 4.1 CRI 定义的退出状态

```protobuf
// k8s.io/cri-api/pkg/apis/runtime/v1/api.proto

message ContainerStatus {
    string id = 1;
    // ...
    int32 exit_code = 6;           // ← exit code
    string reason = 7;             // ← "OOMKilled" 等
    string message = 8;            // ← 详细信息
    Timestamp finished_at = 10;
    
    // 从 K8s 1.28 开始:
    // exit_code 可能通过 signal 区分
    // reason 可以包含更多诊断信息
}
```

### 4.2 kubelet 调用 CRI

```go
// pkg/kubelet/kuberuntime/kuberuntime_container.go
func (m *kubeGenericRuntimeManager) getPodContainerStatuses(
    uid k8stypes.UID, 
    name string, 
    namespace string,
) ([]*kubecontainer.Status, error) {
    
    // 对每个沙箱中的容器调用 CRI
    resp, err := m.runtimeService.ListContainers(ctx, &runtimeapi.ListContainersRequest{
        Filter: &runtimeapi.ContainerFilter{
            PodSandboxId: sandboxID,
        },
    })
    
    for _, c := range resp.Containers {
        statusResp, err := m.runtimeService.ContainerStatus(
            ctx,
            &runtimeapi.ContainerStatusRequest{
                ContainerId: c.Id,
                Verbose:     true,  // ← 获取额外诊断信息
            },
        )
        
        // 构建 kubecontainer.Status
        status := &kubecontainer.Status{
            ID:        kubecontainer.ContainerID{ID: c.Id},
            Name:      c.Metadata.Name,
            Image:     c.Image.Image,
            ExitCode:  int(statusResp.Status.ExitCode),
            Reason:    statusResp.Status.Reason,
            Message:   statusResp.Status.Message,
            StartedAt: ...,
        }
    }
    return statuses, nil
}
```



## 五、kubelet 层的处理逻辑

### 5.1 Pod Status 构建

```go
// pkg/kubelet/kuberuntime/kuberuntime_manager.go
func (m *kubeGenericRuntimeManager) toKubeContainerStatus(
    status *kubecontainer.Status,
    spec *v1.Container,
) v1.ContainerState {
    
    switch {
    case status.State == kubecontainer.ContainerStateRunning:
        return v1.ContainerState{
            Running: &v1.ContainerStateRunning{
                StartedAt: metav1.NewTime(status.StartedAt),
            },
        }
        
    case status.State == kubecontainer.ContainerStateExited:
        return v1.ContainerState{
            Terminated: &v1.ContainerStateTerminated{
                ExitCode:   int32(status.ExitCode),  // ← 核心字段
                Reason:     status.Reason,           // "OOMKilled", "Error"
                Message:    status.Message,
                StartedAt:  metav1.NewTime(status.StartedAt),
                FinishedAt: metav1.NewTime(status.FinishedAt),
                ContainerID: status.ID.ID,
            },
        }
    }
}
```

### 5.2 Pod-level 的聚合逻辑

```
Pod Status Phase 的计算：

┌──────────────────────────────────────────────────────────┐
│  所有容器的状态如何决定 Pod Phase？                         │
│                                                           │
│  if 所有容器正常退出 (exit code 0):                        │
│      → Phase = Succeeded                                  │
│                                                           │
│  if 有容器异常退出 (exit code != 0) 且 restartPolicy != Never: │
│      → Phase = Running (重启中)                           │
│                                                           │
│  if 有容器异常退出 且 restartPolicy == Never:              │
│      → Phase = Failed                                     │
│                                                           │
│  if 所有容器 Ready:                                        │
│      → Conditions.Type=Ready, Status=True                 │
│                                                           │
│  if 有容器 Terminated:                                     │
│      → Conditions.Type=Ready, Status=False                │
│      → Reason: "ContainersNotReady"                       │
└──────────────────────────────────────────────────────────┘
```

### 5.3 Status Manager 的同步

```go
// pkg/kubelet/status/status_manager.go
type manager struct {
    // 内部维护一个 PodStatus 的缓存
    podStatuses      map[types.UID]versionedPodStatus
    
    // 通过 channel 接收新的 status
    podStatusChannel chan podStatusSyncRequest
    
    // 定期（默认 10s）或收到变更时，PATCH 到 API Server
}

func (m *manager) SetPodStatus(pod *v1.Pod, status v1.PodStatus) {
    m.podStatuses[pod.UID] = versionedPodStatus{
        status:       status,
        version:      pod.ResourceVersion,
    }
    // 触发同步
    m.podStatusChannel <- podStatusSyncRequest{uid: pod.UID}
}

func (m *manager) syncPod(uid types.UID, status versionedPodStatus) {
    // 用 PATCH 而不是 PUT，避免竞争
    // patch = strategic merge patch
    // 只更新 status 部分，不影响 spec
    _, err := m.kubeClient.CoreV1().Pods(ns).Patch(
        ctx, name,
        types.StrategicMergePatchType,
        patchData,
        metav1.PatchOptions{},
        "status",  // ← 子资源
    )
}
```

## 六、Kubernetes 中预定义的退出码语义

### 6.1 完整退出码参考表

```
┌──────────┬───────────────────┬──────────────────────────────────┐
│ Exit Code │ 信号 / 含义       │ 在 K8s 中的常见场景               │
├──────────┼───────────────────┼──────────────────────────────────┤
│    0      │ SUCCESS           │ 正常退出，Pod Phase=Succeeded     │
│    1      │ GENERAL_ERROR     │ 应用错误、配置错误、启动失败      │
│    2      │ MISUSE_CMD        │ shell 内建命令误用                │
│   126     │ CMD_CANT_EXEC     │ 命令不可执行（权限不足）          │
│   127     │ CMD_NOT_FOUND     │ 命令/二进制未找到                 │
│   128     │ INVALID_EXIT_ARG  │ exit 命令参数非法                │
│   128+1   │ SIGHUP (1)        │ 终端挂起                         │
│   128+2   │ SIGINT (2)        │ Ctrl+C                          │
│   128+3   │ SIGQUIT (3)       │ Ctrl+\, 核心转储                 │
│   128+4   │ SIGILL (4)        │ 非法指令                         │
│   128+5   │ SIGTRAP (5)       │ 断点陷阱                         │
│   128+6   │ SIGABRT (6)       │ abort() 调用                    │
│   128+7   │ SIGBUS (7)        │ 总线错误                         │
│   128+8   │ SIGFPE (8)        │ 浮点异常                         │
│   128+9   │ SIGKILL (9)       │ ★ OOMKilled / kubelet 强杀       │
│   128+13  │ SIGPIPE (13)      │ 管道断裂（常见于 sidecar）        │
│   128+15  │ SIGTERM (15)      │ ★ 优雅终止（kubectl delete 等）   │
│   128+25  │ SIGXFSZ (25)      │ 文件大小超限                      │
│   255     │ 超出范围           │ exit(-1) 的无符号表示             │
└──────────┴───────────────────┴──────────────────────────────────┘
```

### 6.2 K8s 特有的退出码处理

```go
// pkg/kubelet/kuberuntime/kuberuntime_manager.go (简化)

// kubelet 内部对退出码的一些特殊处理:

// 1. Exit Code 0 → Completed / Succeeded
//    Pod Phase = Succeeded
//    不会重启（如果 restartPolicy=OnFailure 也不会重启）

// 2. Exit Code != 0 → 根据 restartPolicy 决定
//    restartPolicy=Always      → 总是重启（包括 exit 0）
//    restartPolicy=OnFailure   → 非0时重启
//    restartPolicy=Never       → 永不重启

// 3. 容器被 signal 杀死时的特殊处理
//    kubelet 通过 CRI 拿到的 exit code 已经是 128+signal
//    不需要 kubelet 自己计算
```

## 七、重启策略与退出码的交互

### 7.1 重启决策引擎

```go
// pkg/kubelet/kuberuntime/kuberuntime_manager.go
func (m *kubeGenericRuntimeManager) computePodActions(
    ctx context.Context,
    pod *v1.Pod,
    podStatus *kubecontainer.PodStatus,
) podActions {
    
    // 检查每个容器
    for i, container := range pod.Spec.Containers {
        status := podStatus.FindContainerStatusByName(container.Name)
        
        if status == nil || status.State != kubecontainer.ContainerStateExited {
            continue  // 容器还在运行或不存在
        }
        
        // 核心判断逻辑:
        restart := shouldRestartOnFailure(pod)
        
        // restartPolicy=Always:        → 重启（无论 exit code）
        // restartPolicy=OnFailure:     → 仅 exitCode != 0 时重启
        // restartPolicy=Never:         → 不重启
        
        if restart {
            // 检查重启间隔（指数退避）
            // 内部有 backOff 机制，防止频繁重启
            message += fmt.Sprintf(
                "Container %s terminated with exit code %d",
                container.Name, status.ExitCode,
            )
            changes.ContainersToStart[i] = true
        }
    }
}
```

### 7.2 重启间隔的指数退避

```
┌─────────────────────────────────────────────────────┐
│  kubelet 内置的重启退避                               │
│                                                      │
│  第1次重启:  立即                                     │
│  第2次重启:  10s                                      │
│  第3次重启:  20s                                      │
│  第4次重启:  40s                                      │
│  ...                                                 │
│  最大间隔:  300s (5min)                               │
│                                                      │
│  退避公式:  min(last_interval * 2, 300s)              │
│                                                      │
│  容器成功运行超过 10min → 重置退避计时器               │
│                                                      │
│  这就是为什么你会看到 CrashLoopBackOff:               │
│  → kubelet 的 podStatus.Reason = "CrashLoopBackOff"  │
│  → Message 中包含退避的秒数                           │
└─────────────────────────────────────────────────────┘
```

## 八、OOMKilled 的完整链路

```
                    应用分配内存过多
                          │
                          ▼
┌──────────────────────────────────────────────────┐
│                  Linux Kernel                      │
│                                                    │
│  1. 内存分配失败                                    │
│  2. 触发 OOM Killer                                │
│  3. 选择得分最高的进程（oom_score 最大）              │
│     → cgroup 内存超限 → 选择 cgroup 内的进程        │
│  4. 发送 SIGKILL (信号 9)                           │
│  5. 写入 dmesg:                                    │
│     "Out of memory: Killed process 1234 (java)"    │
│     "memory: usage 512MB, limit 256MB"             │
│                                                    │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│            containerd-shim                         │
│                                                    │
│  1. waitpid() 返回 status = SIGKILL (9)            │
│  2. 读取 cgroup memory.events:                     │
│     oom_kill count 从 0 变成 1                     │
│  3. 设置 OOMKilled = true                          │
│  4. exit_code = 137 (128 + 9)                     │
│                                                    │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│              kubelet                               │
│                                                    │
│  Container Status:                                 │
│  {                                                 │
│    "state": {                                      │
│      "terminated": {                               │
│        "exitCode": 137,                            │
│        "reason": "OOMKilled",     ← 区分点        │
│        "startedAt": "...",                         │
│        "finishedAt": "...",                        │
│        "containerID": "containerd://abc123"        │
│      }                                             │
│    }                                               │
│  }                                                 │
│                                                    │
│  → PATCH 到 API Server                             │
│  → 生成 Warning Event:                             │
│    "Back-off restarting failed container"           │
│    "Container oom-killer terminated in 137"        │
│                                                    │
└──────────────────────────────────────────────────┘
```

## 九、PreStop Hook 与退出码

```go
// pkg/kubelet/kuberuntime/kuberuntime_container.go
func (m *kubeGenericRuntimeManager) killContainer(
    ctx context.Context,
    pod *v1.Pod,
    containerID kubecontainer.ContainerID,
    message string,
    reason containerKillReason,
    gracePeriodOverride *int64,
) error {
    
    // 1. 执行 PreStop Hook（如果配置了的话）
    if container.Lifecycle != nil && container.Lifecycle.PreStop != nil {
        // 运行 PreStop，但有超时限制
        // 超时 = min(pod.Spec.TerminationGracePeriodSeconds, 2s 留给后续清理)
        runPreStopHook(ctx, pod, container, containerID)
    }
    
    // 2. 发送 SIGTERM (信号 15)
    //    → 容器收到 SIGTERM
    //    → 容器 PID 1 应该优雅处理
    
    err := m.runtimeService.StopContainer(ctx, &runtimeapi.StopContainerRequest{
        ContainerId: containerID.ID,
        Timeout:     gracePeriodSeconds,
    })
    
    // 3. 如果超时仍未退出 → 发送 SIGKILL (信号 9)
    //    → 容器被强制杀死
    //    → exit code = 137 (128+9)
}

// 整个流程的退出码：
//   如果 PreStop 成功 + 应用在 gracePeriod 内自行退出:
//     → exit code = 应用自定义的（通常是 0 或 143）
//   如果 gracePeriod 超时被 SIGKILL:
//     → exit code = 137
```

## 十、exec liveness/readiness probe 与退出码

```
┌──────────────────────────────────────────────────────────┐
│  Probe 的退出码如何影响容器命运？                           │
│                                                           │
│  livenessProbe:                                           │
│    exec command → exit code 0 → 存活检查通过              │
│    exec command → exit code != 0 → 连续 failureThreshold 次 │
│      → kubelet 杀死容器 (SIGTERM → SIGKILL)               │
│      → 原容器 exit code = 137 或 143                      │
│      → 新容器被启动                                       │
│                                                           │
│  readinessProbe:                                          │
│    exec command → exit code != 0 → Pod Ready=False        │
│    → 不杀死容器，只影响 Service Endpoint                   │
│    → 容器本身不受影响                                     │
│                                                           │
│  startupProbe:                                            │
│    exec command → exit code != 0 → 连续 failureThreshold 次 │
│      → 容器被杀死                                         │
│      → 等同于 livenessProbe 失败的处理                     │
└──────────────────────────────────────────────────────────┘
```

## 十一、kubectl describe 中看到的退出码

```bash
$ kubectl describe pod nginx

Containers:
  nginx:
    State:          Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Mon, 15 Mar 2025 10:00:00 +0000
      Finished:     Mon, 15 Mar 2025 10:05:00 +0000
    Last State:     Terminated
      Reason:       Error
      Exit Code:    1
      Started:      Mon, 15 Mar 2025 09:50:00 +0000
      Finished:     Mon, 15 Mar 2025 09:55:00 +0000
    Restart Count:  2
```

这个输出的底层数据来源：

```
kubectl describe
    │
    │ client-go: Get Pod
    ▼
API Server → etcd
    │
    │ 返回 pod.Status.ContainerStatuses[i].State.Terminated
    │         .LastTerminationState.Terminated
    ▼
格式化输出
```

**`State` vs `LastState` 的底层实现：**

```go
// pkg/kubelet/status/status_manager.go
// kubelet 在构建 status 时：

// State = 当前容器的最新状态
// LastTerminationState = 上一次终止的状态（如果有）

// 这个数据由 kubelet 维护在内存中
// 通过 containerStatuses 数组来追踪历史
// 每次容器重启时，当前状态 → LastState，新状态 → State
```

## 十二、完整源码关键路径

```bash
# 1. Linux Kernel → 容器进程退出
# (不是 K8s 代码，但本质)

# 2. containerd-shim 捕获退出码
containerd/
├── cmd/containerd-shim-runc-v2/
│   └── process/init.go           # waitpid() + exit code 捕获
├── runtime/v2/runc/
│   └── container.go              # 容器状态管理
└── pkg/cri/server/
    └── container_status.go       # CRI ContainerStatus 实现

# 3. kubelet 通过 CRI 获取状态
pkg/kubelet/kuberuntime/
├── kuberuntime_container.go      # getPodContainerStatuses()
├── kuberuntime_manager.go        # computePodActions(), toKubeContainerStatus()
└── kuberuntime_gc.go             # 垃圾回收旧容器

# 4. kubelet 构建 Pod Status
pkg/kubelet/
├── status/
│   └── status_manager.go         # status 同步到 API Server
├── prober/
│   └── prober.go                 # probe 结果影响状态
└── kubelet_pods.go               # convertStatusToAPIStatus()

# 5. API Server 存储
pkg/registry/core/pod/
└── strategy.go                   # status 子资源的验证逻辑
```

## 十三、实战排查速查

```
┌──────────┬──────────────────────┬─────────────────────────────────────┐
│ Exit Code │ 含义                │ 排查方向                              │
├──────────┼──────────────────────┼─────────────────────────────────────┤
│   0       │ 正常退出             │ 检查 Pod 是否期望一次性任务           │
│   1       │ 应用内部错误          │ 应用日志: kubectl logs --previous    │
│   126     │ 权限不足             │ 检查文件权限、SecurityContext        │
│   127     │ 命令未找到            │ 检查 entrypoint/command 拼写        │
│   137     │ 被 SIGKILL           │ 优先检查 OOM: dmesg | grep oom      │
│           │                      │ 检查 limits.memory 配置              │
│           │                      │ 也可能是 kubelet 主动杀死            │
│   139     │ SIGSEGV              │ 段错误，检查代码或兼容性             │
│   143     │ SIGTERM              │ 正常优雅终止（kubectl delete 等）    │
│           │                      │ 检查 preStop hook 和信号处理         │
│   255     │ exit(-1)             │ 应用代码中 exit(-1) 或异常退出       │
└──────────┴──────────────────────┴─────────────────────────────────────┘
```

```bash
# 查看上次容器退出的详细日志
kubectl logs <pod> --previous

# 查看内核 OOM 日志（需要节点权限）
dmesg | grep -i "oom\|killed process"

# 查看容器的详细状态（包含 exit code 历史）
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[*]}'

# 查看 cgroup 的 OOM 计数（需要节点权限）
cat /sys/fs/cgroup/memory/kubepods/.../memory.oom_control
```

---

**总结一句话**：Pod exit code 是 Linux 进程退出码（0-255）的直接映射——容器 runtime 的 shim 进程通过 `waitpid()` 捕获，通过 CRI gRPC 传递给 kubelet，kubelet 将其填充到 `ContainerStateTerminated.ExitCode` 并 PATCH 到 API Server 的 Pod Status 中；其中 128+信号号 是被信号杀死的标志，137 特别重要因为它是 OOMKilled 的典型表现，但需要 runtime 检测到 cgroup 的 `memory.events.oom_kill` 才会标记 `Reason: OOMKilled`。
