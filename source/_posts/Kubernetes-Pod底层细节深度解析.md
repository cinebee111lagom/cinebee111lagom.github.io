---
title: Kubernetes Pod 底层细节 — 深度解析
date: 2026-09-07 11:30:00
tags:
  - Kubernetes
  - Namespace
  - cgroup
  - containerd
  - eBPF
categories:
  - Kubernetes
---

# Underlying Details — Deep Dive

# 底层细节 — 深度解析

---

## 1. Linux Namespaces — The Foundation of Isolation

### 1.1 Six Namespace Types Used by Pods

Every Kubernetes pod relies on Linux kernel namespaces for isolation:

每个 Kubernetes Pod 都依赖 Linux 内核命名空间来实现隔离：

```
Namespace        System Call Flag       Purpose / 用途
─────────────────────────────────────────────────────────────
PID              CLONE_NEWPID           Process ID isolation
                                         进程 ID 隔离

Network (net)    CLONE_NEWNET           Network stack isolation
                                         网络协议栈隔离

Mount (mnt)      CLONE_NEWNS            Filesystem mount points
                                         文件系统挂载点隔离

UTS              CLONE_NEWUTS           Hostname isolation
                                         主机名隔离

IPC              CLONE_NEWIPC           Shared memory / semaphores
                                         共享内存 / 信号量隔离

User             CLONE_NEWUSER          UID/GID mapping
                                         UID/GID 映射隔离
```

### 1.2 How Namespaces Are Created for a Pod

```bash
# When Kubelet tells containerd to create a pod sandbox:
# 当 Kubelet 告诉 containerd 创建 Pod 沙箱时：

# Step 1: Create network namespace
# 步骤 1：创建网络命名空间
$ ip netns add cni-abc123-def456
$ ls /var/run/netns/
cni-abc123-def456

# Step 2: CNI plugin configures the namespace
# 步骤 2：CNI 插件配置命名空间
$ CNI_COMMAND=ADD \
  CNI_CONTAINERID=abc123 \
  CNI_NETNS=/var/run/netns/cni-abc123-def456 \
  CNI_IFNAME=eth0 \
  /opt/cni/bin/bridge < /etc/cni/net.d/10-bridge.conflist

# Step 3: Verify from inside the namespace
# 步骤 3：从命名空间内部验证
$ ip netns exec cni-abc123-def456 ip addr show eth0
3: eth0@if42: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450
    link/ether 6a:bb:88:33:11:99 brd ff:ff:ff:ff:ff:ff
    inet 10.244.1.5/24 brd 10.244.1.255 scope global eth0
```

---

## 2. Veth Pair — The Pod-to-Node Pipe

### 2.1 What Is a Veth Pair?

A veth (virtual ethernet) pair is a **kernel-level pipe** with two endpoints. Packets entering one end emerge from the other:

Veth（虚拟以太网）对是一个具有两个端点的**内核级管道**。进入一端的数据包从另一端出来：

```
Pod Network Namespace              Node Network Namespace
Pod 网络命名空间                    节点网络命名空间

┌───────────────────┐             ┌───────────────────┐
│                   │             │                   │
│   eth0            │             │   vethXXXXXX      │
│   (veth end A)    │◄───────────►│   (veth end B)    │
│   10.244.1.5      │  kernel     │                   │
│                   │  bridge     │   ┌───────────┐   │
│                   │             │   │  cbr0 /    │   │
│                   │             │   │  cni0      │   │
│                   │             │   │  10.244.1.1│   │
└───────────────────┘             └───┴───────────┴───┘
                                         │
                                    Node routing table
                                    节点路由表
                                         │
                                    Physical NIC (eth0)
                                    物理网卡
```

### 2.2 Creating a Veth Pair (Kernel-Level View)

```bash
# The CNI plugin does this automatically, but here is the raw process:
# CNI 插件会自动完成这些，但以下是原始过程：

# Create veth pair / 创建 veth 对
$ ip link add veth_pod_A type veth peer name veth_node_B

# Move one end into the pod's network namespace
# 将一端移入 Pod 的网络命名空间
$ ip link set veth_pod_A netns cni-abc123-def456

# Inside pod namespace: configure IP
# 在 Pod 命名空间内：配置 IP
$ ip netns exec cni-abc123-def456 bash -c "
  ip addr add 10.244.1.5/24 dev veth_pod_A
  ip link set veth_pod_A up
  ip link set lo up
  ip route add default via 10.244.1.1
"

# On node: attach other end to bridge
# 在节点上：将另一端连接到网桥
$ ip link set veth_node_B master cni0
$ ip link set veth_node_B up
```

### 2.3 Packet Journey (Pod → External)

```
Step-by-step packet path from pod to outside world:
从 Pod 到外部网络的数据包逐步路径：

[1] Application calls send()
    应用程序调用 send()
        │
        ▼
[2] Socket buffer (sk_buff) created in pod's network namespace
    在 Pod 的网络命名空间中创建套接字缓冲区（sk_buff）
        │
        ▼
[3] TCP/IP stack processing (pod namespace)
    TCP/IP 协议栈处理（Pod 命名空间）
    - Source IP: 10.244.1.5
    - Dest IP: 8.8.8.8
        │
        ▼
[4] Routing table lookup → default via 10.244.1.1 → eth0
    路由表查找 → 默认网关 10.244.1.1 → eth0
        │
        ▼
[5] sk_buff passes through veth pair (kernel memory, zero-copy)
    sk_buff 通过 veth 对传递（内核内存，零拷贝）
        │
        ▼
[6] sk_buff arrives on node's cbr0 bridge interface
    sk_buff 到达节点的 cbr0 网桥接口
        │
        ▼
[7] Bridge forwarding decision:
    网桥转发决策：
    - Destination MAC is bridge itself → pass to L3
      目标 MAC 是网桥自身 → 传到 L3
        │
        ▼
[8] Node routing table lookup:
    节点路由表查找：
    - 10.244.1.0/24 → cbr0 (already came from here)
    - 0.0.0.0/0 → default via 192.168.1.1 dev eth0
        │
        ▼
[9] NAT (iptables POSTROUTING — MASQUERADE)
    NAT（iptables POSTROUTING — MASQUERADE）
    - Source IP changed: 10.244.1.5 → 192.168.1.10
    - 源 IP 修改：10.244.1.5 → 192.168.1.10
        │
        ▼
[10] Physical NIC transmits frame
     物理网卡发送帧
```

---

## 3. iptables — The kube-proxy Engine

### 3.1 How kube-proxy Translates Services to iptables Rules

When a Service is created, kube-proxy installs iptables rules on **every node**:

当创建 Service 时，kube-proxy 在**每个节点**上安装 iptables 规则：

```bash
# Service: llm-inference-svc (ClusterIP: 10.96.0.50:80)
# Backend Pods: 10.244.1.5:8000, 10.244.2.8:8000, 10.244.3.12:8000

# kube-proxy creates these iptables chains:
# kube-proxy 创建以下 iptables 链：

# === NAT table ===
# === NAT 表 ===

# Chain: KUBE-SERVICES — entry point
-A KUBE-SERVICES -d 10.96.0.50/32 -p tcp -m tcp --dport 80 \
  -j KUBE-SVC-XXXXYYYY

# Chain: KUBE-SVC-XXXXYYYY — load balancing (random selection)
# Uses probability-based selection for equal distribution
# 使用基于概率的选择实现均匀分布
-A KUBE-SVC-XXXXYYYY -m statistic --mode random --probability 0.3333 \
  -j KUBE-SEP-AAAAAAAA
-A KUBE-SVC-XXXXYYYY -m statistic --mode random --probability 0.5000 \
  -j KUBE-SEP-BBBBBBBB
-A KUBE-SVC-XXXXYYYY -j KUBE-SEP-CCCCCCCC

# Chain: KUBE-SEP-AAAAAAAA — DNAT to pod
# DNAT 到 Pod
-A KUBE-SEP-AAAAAAAA -p tcp -m tcp -j DNAT --to-destination 10.244.1.5:8000

# Chain: KUBE-SEP-BBBBBBBB
-A KUBE-SEP-BBBBBBBB -p tcp -m tcp -j DNAT --to-destination 10.244.2.8:8000

# Chain: KUBE-SEP-CCCCCCCC
-A KUBE-SEP-CCCCCCCC -p tcp -m tcp -j DNAT --to-destination 10.244.3.12:8000
```

### 3.2 conntrack — Connection Tracking

```
Every connection through kube-proxy is tracked in the conntrack table:
通过 kube-proxy 的每个连接都在 conntrack 表中被跟踪：

$ conntrack -L -p tcp --dport 8000

tcp  6 86398 ESTABLISHED src=10.244.0.3 dst=10.96.0.50 sport=48832 dport=80
  src=10.244.1.5 dst=10.244.0.3 sport=8000 dport=48832 [ASSURED] use=1

Key insight:
关键洞察：
- Original:    10.244.0.3:48832 → 10.96.0.50:80
- Reply:       10.244.1.5:8000 → 10.244.0.3:48832
- NAT reverses automatically on reply packets
  NAT 在回复包上自动反转
```

**Scaling Problem / 扩展性问题：**

```
With N services × M endpoints:
对于 N 个 Service × M 个端点：

iptables rules count = O(N × M)
iptables 规则数 = O(N × M)

At 10,000 services × 10 endpoints = 100,000+ iptables rules
当 10,000 个 Service × 10 个端点 = 100,000+ 条 iptables 规则

- Rule insertion takes 5-30 minutes
  规则插入需要 5-30 分钟
- Every connection traverses the full chain
  每个连接都遍历完整的链
- This is why large clusters migrate to Cilium/eBPF
  这就是大型集群迁移到 Cilium/eBPF 的原因
```

---

## 4. eBPF — The Modern Alternative (Cilium)

### 4.1 eBPF Program Placement

```
┌──────────────────────────────────────────────────────┐
│                    Linux Kernel                       │
│                                                      │
│  ┌────────────────┐       ┌───────────────────────┐  │
│  │ XDP (eBPF)     │       │ TC (Traffic Control)  │  │
│  │ Earliest hook  │       │ Post-routing hook     │  │
│  │ Before skb     │       │                       │  │
│  │ allocation     │       │                       │  │
│  └───────┬────────┘       └──────────┬────────────┘  │
│          │                           │               │
│          ▼                           ▼               │
│  ┌────────────────────────────────────────────────┐  │
│  │         BPF Maps (Hash Tables)                 │  │
│  │                                                │  │
│  │  Service Map:                                  │  │
│  │  ┌──────────────────┬───────────────────────┐  │  │
│  │  │ Key: 10.96.0.50:80│ Value: Pod backend   │  │  │
│  │  │                   │ 10.244.1.5:8000 (33%)│  │  │
│  │  │                   │ 10.244.2.8:8000 (33%)│  │  │
│  │  │                   │ 10.244.3.12:8000(34%)│  │  │
│  │  └──────────────────┴───────────────────────┘  │  │
│  │                                                │  │
│  │  Conntrack Map:                                │  │
│  │  ┌──────────────────┬───────────────────────┐  │  │
│  │  │ Key: 5-tuple     │ Value: NAT state      │  │  │
│  │  └──────────────────┴───────────────────────┘  │  │
│  │                                                │  │
│  │  Policy Map:                                   │  │
│  │  ┌──────────────────┬───────────────────────┐  │  │
│  │  │ Key: identity ID │ Value: allow/deny     │  │  │
│  │  └──────────────────┴───────────────────────┘  │  │
│  └────────────────────────────────────────────────┘  │
│          │                                           │
│          ▼                                           │
│  Packet forwarded directly to destination Pod's veth │
│  数据包直接转发到目标 Pod 的 veth                       │
└──────────────────────────────────────────────────────┘

Key difference from iptables:
与 iptables 的关键区别：

- O(1) hash map lookup instead of O(n) rule traversal
  O(1) 哈希表查找，而非 O(n) 规则遍历
- Runs at XDP level (before skb allocation) for maximum speed
  在 XDP 级别运行（在 skb 分配之前），实现最大速度
- Supports DSR (Direct Server Return) — reply bypasses LB
  支持 DSR（直接服务器返回）— 回复绕过负载均衡器
```

---

## 5. Container Runtime Deep Dive (containerd)

### 5.1 Pod Creation Sequence

```
Kubelet                          containerd                    runc
   │                                  │                          │
   │  RunPodSandbox(PodSpec)          │                          │
   │─────────────────────────────────▶│                          │
   │                                  │                          │
   │                                  │  Create network NS       │
   │                                  │────── CNI plugin ───────▶│
   │                                  │        │                 │
   │                                  │        │ create veth     │
   │                                  │        │ assign IP       │
   │                                  │        │ setup routes    │
   │                                  │◀───────┘                 │
   │                                  │                          │
   │  CreateContainer(SandboxID,      │                          │
   │    ImageSpec, Mounts, Env)       │                          │
   │─────────────────────────────────▶│                          │
   │                                  │                          │
   │                                  │  Pull image (if needed)  │
   │                                  │─────────────────────────▶│
   │                                  │  (registry → content     │
   │                                  │   store)                 │
   │                                  │                          │
   │                                  │  Create container spec   │
   │                                  │  (OCI runtime spec)      │
   │                                  │                          │
   │                                  │  runc create             │
   │                                  │─────────────────────────▶│
   │                                  │         │                │
   │                                  │         │ clone() with   │
   │                                  │         │ namespace flags│
   │                                  │         │                │
   │                                  │         │ set cgroups    │
   │                                  │         │                │
   │                                  │         │ pivot_root     │
   │                                  │         │ (new rootfs)   │
   │                                  │         │                │
   │                                  │◀────────┘                │
   │                                  │                          │
   │  StartContainer(ContainerID)     │                          │
   │─────────────────────────────────▶│                          │
   │                                  │  runc start              │
   │                                  │─────────────────────────▶│
   │                                  │  (exec entrypoint)       │
   │                                  │                          │
   │  [Container PID 1 running]       │                          │
   │◀────────────────────────────────│                          │
```

### 5.2 OCI Runtime Spec Generated by containerd

```json
{
  "ociVersion": "1.0.2",
  "process": {
    "terminal": false,
    "user": { "uid": 0, "gid": 0 },
    "args": ["python", "-m", "vllm.entrypoints.openai.api_server",
             "--model", "/models/llama-70b",
             "--tensor-parallel-size", "2"],
    "env": [
      "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
      "NVIDIA_VISIBLE_DEVICES=0,1",
      "CUDA_VERSION=12.2"
    ],
    "cwd": "/"
  },
  "root": {
    "path": "rootfs",
    "readonly": true
  },
  "linux": {
    "namespaces": [
      { "type": "pid" },
      { "type": "network" },
      { "type": "ipc" },
      { "type": "uts" },
      { "type": "mount" },
      { "type": "cgroup" }
    ],
    "resources": {
      "memory": {
        "limit": 68719476736
      },
      "cpu": {
        "quota": 1600000,
        "period": 100000
      },
      "devices": [
        {
          "allow": true,
          "access": "rwm",
          "type": "c",
          "major": 195,
          "minor": 0
        }
      ]
    },
    "cgroupsPath": "/kubepods/burstable/pod-uid/container-id",
    "maskedPaths": ["/proc/kcore", "/proc/sysrq-trigger"],
    "readonlyPaths": ["/proc/asound", "/proc/bus"]
  },
  "mounts": [
    {
      "destination": "/dev/shm",
      "type": "tmpfs",
      "source": "shm",
      "options": ["nosuid", "noexec", "nodev", "mode=1777", "size=8589934592"]
    },
    {
      "destination": "/models",
      "type": "bind",
      "source": "/var/lib/kubelet/pods/uid/volumes/kubernetes.io~pv/model-pvc",
      "options": ["rbind", "rprivate", "ro"]
    }
  ]
}
```

---

## 6. Cgroups v2 — Resource Control

### 6.1 Cgroup Hierarchy for a Pod

```
/sys/fs/cgroup/
├── kubepods.slice/
│   ├── kubepods-burstable.slice/          ← QoS class: Burstable
│   │   ├── kubepods-burstable-pod<UID>.slice/  ← Pod-level cgroup
│   │   │   │
│   │   │   ├── containerd-<CID>.scope/    ← Main container
│   │   │   │   ├── memory.max = 68719476736    (64 GiB)
│   │   │   │   ├── memory.current             (actual usage)
│   │   │   │   ├── cpu.max = "1600000 100000"  (16 cores)
│   │   │   │   ├── cpu.stat                   (usage stats)
│   │   │   │   ├── pids.max = 4194304
│   │   │   │   └── io.max                     (disk I/O limits)
│   │   │   │
│   │   │   ├── containerd-<SID>.scope/    ← Sidecar (envoy)
│   │   │   │   ├── memory.max = 536870912     (512 MiB)
│   │   │   │   └── cpu.max = "200000 100000"  (2 cores)
│   │   │   │
│   │   │   └── containerd-<AID>.scope/    ← Init container (done)
│   │   │
│   │   └── ... (other burstable pods)
│   │
│   └── kubepods-guaranteed.slice/         ← QoS class: Guaranteed
│       └── ...
```

### 6.2 Memory Pressure Behavior

```
When a container approaches its memory limit:
当容器接近其内存限制时：

1. Kernel triggers memory reclaim
   内核触发内存回收
   - File-backed pages dropped (if not modified)
     文件支持的页面被丢弃（如果未修改）
   - Anonymous pages swapped (if swap enabled)
     匿名页面被交换（如果启用了 swap）

2. If reclaim fails and limit is hit:
   如果回收失败且达到限制：
   - cgroup OOM killer invoked
     cgroup OOM killer 被调用
   - Selects the process with highest oom_score within the cgroup
     选择 cgroup 内 oom_score 最高的进程
   - Sends SIGKILL
     发送 SIGKILL

3. Kubelet sees container exit code 137 (SIGKILL)
   Kubelet 看到容器退出码 137（SIGKILL）
   - Pod status: OOMKilled
   - If restartPolicy: Always → kubelet restarts the container
     如果 restartPolicy: Always → kubelet 重启容器
```

```bash
# Monitor real-time cgroup memory usage:
# 实时监控 cgroup 内存使用：

$ cat /sys/fs/cgroup/kubepods-burstable-pod<UID>.slice/containerd-<CID>.scope/memory.current
5497558138880   # 5.1 GiB in bytes

$ cat /sys/fs/cgroup/kubepods-burstable-pod<UID>.slice/containerd-<CID>.scope/memory.stat
anon 51539607552          # Anonymous memory (heap, stack) / 匿名内存
file 2147483648           # Page cache / 页面缓存
slab 134217728            # Kernel slab allocator / 内核 slab 分配器
sock 67108864             # Socket buffers / 套接字缓冲区
pgfault 1048576
pgmajfault 256
oom_kill 0                # OOM kill count / OOM 杀死计数
```

---

## 7. Image Storage — Layer-Based Architecture

### 7.1 Container Image Layers

```
┌───────────────────────────────────────────────┐
│  vllm/vllm-openai:latest                      │
│                                               │
│  Layer 5 (top):  COPY vllm source code        │  ← 200 MB
│  ─────────────────────────────────────────    │
│  Layer 4:        pip install dependencies      │  ← 3.2 GB (CUDA, torch)
│  ─────────────────────────────────────────    │
│  Layer 3:        Install Python 3.10           │  ← 150 MB
│  ─────────────────────────────────────────    │
│  Layer 2:        Install system packages       │  ← 80 MB
│  ─────────────────────────────────────────    │
│  Layer 1 (base): Ubuntu 22.04                  │  ← 77 MB
└───────────────────────────────────────────────┘

Total compressed:   ~1.8 GB
Total uncompressed: ~3.7 GB

Storage location on node:
节点上的存储位置：

/var/lib/containerd/io.containerd.content.v1.content/blobs/sha256/
├── a1b2c3... (Layer 1 - compressed)
├── d4e5f6... (Layer 2 - compressed)
├── g7h8i9... (Layer 3 - compressed)
├── j0k1l2... (Layer 4 - compressed)
└── m3n4o5... (Layer 5 - compressed)

OverlayFS mount (container view):
OverlayFS 挂载（容器视图）：

/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/
├── 1/ (Layer 1 — lower)
├── 2/ (Layer 2 — lower)
├── 3/ (Layer 3 — lower)
├── 4/ (Layer 4 — lower)
└── 5/ (Layer 5 — upper, writable if needed)

Container rootfs = overlay mount with all layers stacked
容器根文件系统 = 所有层堆叠的 overlay 挂载
```

### 7.2 OverlayFS Mount Command (What containerd Does)

```bash
# What containerd executes internally:
# containerd 内部执行的操作：

$ mount -t overlay overlay \
  -o lowerdir=/snapshots/1/fs:/snapshots/2/fs:/snapshots/3/fs:/snapshots/4/fs:/snapshots/5/fs, \
     upperdir=/snapshots/6/fs, \
     workdir=/snapshots/6/work \
  /run/containerd/io.containerd.runtime.v2.task/<CID>/rootfs

# Inside the container, the app sees a unified filesystem:
# 在容器内部，应用程序看到的是统一的文件系统：
$ ls /
bin  boot  dev  etc  home  lib  models  opt  proc  root  sbin  sys  tmp  usr  var
```

---

## 8. DNS Resolution Inside a Pod

### 8.1 /etc/resolv.conf Injection

```bash
# Kubelet writes this to the pod's /etc/resolv.conf:
# Kubelet 将以下内容写入 Pod 的 /etc/resolv.conf：

$ cat /etc/resolv.conf
search default.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10      # CoreDNS ClusterIP
options ndots:5
```

### 8.2 DNS Resolution Path

```
Application resolves "llm-inference-svc":
应用程序解析 "llm-inference-svc"：

[1] libc reads /etc/resolv.conf
    libc 读取 /etc/resolv.conf

[2] Search domain expansion (ndots:5 means if < 5 dots, try search domains):
    搜索域扩展（ndots:5 表示如果少于 5 个点，尝试搜索域）：

    Try 1: llm-inference-svc.default.svc.cluster.local
    Try 2: llm-inference-svc.svc.cluster.local
    Try 3: llm-inference-svc.cluster.local
    Try 4: llm-inference-svc (absolute, if no dots)

[3] DNS query sent to CoreDNS (10.96.0.10:53)
    DNS 查询发送到 CoreDNS

[4] CoreDNS resolves using kubernetes plugin:
    CoreDNS 使用 kubernetes 插件解析：
    - Queries API server for Service "llm-inference-svc" in namespace "default"
      向 API Server 查询 "default" 命名空间中的 Service "llm-inference-svc"
    - Returns ClusterIP: 10.96.0.50
      返回 ClusterIP: 10.96.0.50

[5] For headless services (ClusterIP: None):
    对于 Headless Service（ClusterIP: None）：
    - Returns individual Pod IPs: 10.244.1.5, 10.244.2.8, 10.244.3.12
      返回各个 Pod IP
    - Client-side load balancing
      客户端负载均衡
```

---

## 9. Network Policy Enforcement (Cilium eBPF)

### 9.1 How Policies Become eBPF Programs

```
NetworkPolicy YAML
       │
       ▼
┌────────────────────────┐
│ Cilium Agent (DaemonSet)│
│ Watches K8s API for:   │
│ - NetworkPolicy         │
│ - CiliumNetworkPolicy   │
│ - Endpoints             │
│ - Services              │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Policy Compiler                        │
│                                        │
│ Input:                                 │
│   ingress: from podSelector app=web    │
│   ports: TCP 8000                      │
│                                        │
│ Output:                                │
│   identity=42 (app=web) → allow:8000   │
│   default → deny                       │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ BPF Program Compilation                │
│                                        │
│ Compiled into bytecode that runs at:   │
│ - TC (Traffic Control) hook on veth    │
│   在 veth 上的 TC 钩子运行              │
│                                        │
│ Packet lookup path:                    │
│   1. Extract source identity from      │
│      source pod's BPF map entry        │
│      从源 Pod 的 BPF map 条目提取源身份  │
│   2. Lookup policy map:                │
│      {src_identity, dst_port} → allow? │
│      查找策略映射表                      │
│   3. If no match → DROP packet         │
│      如果没有匹配 → 丢弃数据包           │
└────────────────────────────────────────┘
```

### 9.2 Identity-Based Security (Not IP-Based)

```
Traditional (iptables):
传统方式（iptables）：

  Rules match on IP addresses
  规则匹配 IP 地址
  Problem: Pod IPs change on restart
  问题：Pod 重启时 IP 会变

Cilium (identity-based):
Cilium（基于身份）：

  Each pod gets a numeric identity assigned at creation
  每个 Pod 在创建时获得一个数字身份

  Identity derived from labels:
  身份从标签派生：
    app=llm-inference, version=v2 → identity=1234

  Policies reference identities, not IPs:
  策略引用身份，而非 IP：

  ┌──────────────────────────────────────────┐
  │ BPF Policy Map                           │
  │                                          │
  │ Source Identity │ Destination │ Port │ Verdict │
  │ 1234           │ 5678        │ 8000 │ ALLOW  │
  │ 1234           │ 5678        │ *    │ DROP   │
  │ 9999           │ 5678        │ *    │ ALLOW  │ (admin)
  │ *              │ 5678        │ *    │ DROP   │ (default)
  └──────────────────────────────────────────┘

  Pod restarts with new IP 10.244.5.99 → same identity → same policy
  Pod 使用新 IP 重启 → 身份不变 → 策略不变
```

---

## 10. Process Lifecycle Inside the Container

### 10.1 PID 1 Problem

```
In a normal Linux system:
在普通 Linux 系统中：

  init (PID 1) → manages zombie processes
  init（PID 1）→ 管理僵尸进程

In a container:
在容器中：

  Your application IS PID 1
  你的应用程序就是 PID 1

  This means:
  这意味着：

  1. SIGTERM handling — if app doesn't trap SIGTERM, it won't gracefully shut down
     SIGTERM 处理 — 如果应用不捕获 SIGTERM，它不会优雅关闭
     → Kubernetes waits terminationGracePeriodSeconds (default 30s)
       然后 sends SIGKILL
       Kubernetes 等待 terminationGracePeriodSeconds（默认 30 秒），然后发送 SIGKILL

  2. Zombie reaping — orphaned child processes become zombies
     僵尸进程回收 — 孤儿子进程变为僵尸进程
     → Use tini or dumb-init as PID 1 entrypoint
       使用 tini 或 dumb-init 作为 PID 1 入口

  3. Signal forwarding:
     信号转发：
     PID 1 (tini) → forwards SIGTERM → child process (your app)
```

### 10.2 Graceful Shutdown Sequence

```
Time    Event
──────────────────────────────────────────────────

t=0     User runs: kubectl delete pod llm-inference-pod
        用户运行删除命令

t=0.1   API Server sets pod.deletionTimestamp
        API Server 设置删除时间戳

t=0.2   Kubelet sees deletion, begins shutdown:
        Kubelet 检测到删除，开始关闭：

t=0.3   [1] Pod removed from Service endpoints
             (new connections stop flowing)
             Pod 从 Service 端点中移除（新连接停止流入）

t=0.5   [2] PreStop hook executed (if defined)
             执行 PreStop 钩子（如果已定义）
             Example: sleep 15 (let in-flight requests complete)
             示例：sleep 15（让正在处理的请求完成）

t=15.5  [3] SIGTERM sent to PID 1 in container
             向容器中的 PID 1 发送 SIGTERM
             - vLLM starts graceful shutdown
               vLLM 开始优雅关闭
             - Drains active inference requests
               排空活跃的推理请求
             - Releases GPU memory
               释放 GPU 内存

t=30    [4] terminationGracePeriodSeconds exceeded
             超过 terminationGracePeriodSeconds
             SIGKILL sent to all processes
             向所有进程发送 SIGKILL

t=30.1  [5] Container stopped, network namespace torn down
             容器停止，网络命名空间被拆除
             - Veth pair deleted
               Veth 对被删除
             - IP released back to IPAM
               IP 释放回 IPAM
             - Cgroup removed
               Cgroup 被移除

t=30.2  [6] Pod object deleted from API Server
             Pod 对象从 API Server 中删除
```

```yaml
# Recommended graceful shutdown config for inference pods:
# 推荐的推理 Pod 优雅关闭配置：
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference-pod
spec:
  terminationGracePeriodSeconds: 120   # Longer for large models
                                       # 大模型需要更长时间
  containers:
    - name: inference
      lifecycle:
        preStop:
          exec:
            command:
              - /bin/sh
              - -c
              - "sleep 15"   # Wait for endpoint propagation
                             # 等待端点传播
```

---

## Summary — The Complete Stack

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 7:  HTTP API (vLLM / TGI server)                      │
│           应用层: HTTP API 服务                               │
├─────────────────────────────────────────────────────────────┤
│ Layer 6:  Container Process (PID 1, entrypoint)             │
│           容器进程层: PID 1, 入口进程                         │
├─────────────────────────────────────────────────────────────┤
│ Layer 5:  Filesystem (OverlayFS, image layers + PVC mounts) │
│           文件系统层: OverlayFS, 镜像层 + PVC 挂载            │
├─────────────────────────────────────────────────────────────┤
│ Layer 4:  Resource Control (cgroups v2 — CPU, memory, GPU)  │
│           资源控制层: cgroups v2 — CPU, 内存, GPU             │
├─────────────────────────────────────────────────────────────┤
│ Layer 3:  Isolation (Linux namespaces — pid, net, mnt, uts) │
│           隔离层: Linux 命名空间 — pid, net, mnt, uts         │
├─────────────────────────────────────────────────────────────┤
│ Layer 2:  Networking (veth pair → bridge → iptables/eBPF)   │
│           网络层: veth 对 → 网桥 → iptables/eBPF             │
├─────────────────────────────────────────────────────────────┤
│ Layer 1:  Container Runtime (containerd → runc)             │
│           容器运行时层: containerd → runc                     │
├─────────────────────────────────────────────────────────────┤
│ Layer 0:  Linux Kernel (sched, netfilter, device drivers)   │
│           Linux 内核: 调度器, netfilter, 设备驱动             │
└─────────────────────────────────────────────────────────────┘
```

Every layer interacts with the layers above and below through well-defined interfaces. Understanding these underlying details is essential for troubleshooting performance issues, network failures, and resource contention in production inference workloads.

每一层通过定义良好的接口与上下层交互。理解这些底层细节对于排查生产推理工作负载中的性能问题、网络故障和资源争用至关重要。
