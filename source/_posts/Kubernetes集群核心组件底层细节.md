---
title: Kubernetes 集群核心组件底层细节
date: 2026-09-08 11:00:00
tags:
  - Kubernetes
  - etcd
  - kube-apiserver
  - kubelet
categories:
  - Kubernetes
---

## 控制平面组件（Control Plane）

### `kube-apiserver` v1.35.1 (27.7MB)

集群的**唯一入口**，所有组件之间的通信都经过它。

- 提供 RESTful API（gRPC + HTTP/JSON）
- 认证（Authentication）→ 鉴权（Authorization）→ 准入控制（Admission Control）三层过滤链
- 将资源对象持久化到 etcd
- 内部维护一个 **WatchCache**，支持高效的 `list/watch` 机制，是 Informer 机制的根基
- 默认监听 6443 端口（HTTPS），也暴露 8080 非安全端口（本地）

### `kube-controller-manager` v1.35.1 (23.1MB)

一个进程内打包了**几十个控制器**的控制循环：

| 控制器 | 职责 |
|---|---|
| ReplicaSet Controller | 确保 Pod 副本数 = 期望值 |
| Deployment Controller | 管理滚动更新、回滚 |
| Node Controller | 监控节点心跳，标记 NotReady/驱逐 |
| Service Account Controller | 为每个 NS 自动创建 default SA |
| Endpoint Controller | 监听 Service + Pod 变化，维护 Endpoints |
| Job/CronJob Controller | 管理批处理任务 |
| Garbage Collector | 级联删除（OwnerReference）|
| … | 共约 30+ 个 |

每个控制器都是独立的 goroutine，通过 **Informer** 机制 watch API Server，本地缓存（`DeltaFIFO`），用 **List-Watch** 保证最终一致性。

### `kube-scheduler` v1.35.1 (17.2MB)

决定 Pod 跑在哪个节点上，分两个阶段：

```
Filtering（过滤）  →  所有不满足条件的节点被淘汰
   ↓
Scoring（打分）    →  对剩余节点加权打分
   ↓
Binding（绑定）    →  向 API Server 写入 binding，kubelet 拉起 Pod
```

- 支持**抢占（Preemption）**：高优先级 Pod 可以驱逐低优先级
- 支持调度框架插件化（Scheduling Framework），自定义 Filter/Score/Reserve/Permit/Bind
- 默认对**同一 Deployment 的 Pod 做打散**（PodTopologySpread / PodAffinity）

### `etcd` 3.6.6-0 (23.6MB)

**唯一的持久化存储**，整个集群的状态都在这里。

- 基于 **Raft 共识协议**，写入需要多数节点确认（quorum）
- 数据模型：分层 key-value，路径类似 `/registry/pods/default/my-pod`
- MVCC（多版本并发控制），支持 watch 历史版本
- 默认使用 gRPC + protobuf 通信
- 性能瓶颈点：磁盘 I/O（建议 SSD），定期 compaction + defrag
- 在 kind/minikube 中是**单节点**，生产环境至少 3 或 5 个节点

---

## 数据平面组件（Data Plane）

### `kube-proxy` v1.35.1 (25.7MB)

负责在每个节点上实现 **Service 的网络代理**，即 ClusterIP / NodePort / LoadBalancer 的流量转发。

三种实现模式：

| 模式 | 底层机制 | 特点 |
|---|---|---|
| **iptables** | 内核 iptables 规则链 | 成熟稳定，规则数 O(n)，Service 多时有性能问题 |
| **ipvs** | 内核 IPVS 模块（L4 LB） | O(1) 查找，支持多种负载均衡算法（rr/lc/sh...） |
| **nftables** | nftables (较新) | iptables 的继任者，1.29+ 引入 |
| **userspace** | 用户态转发 | 已废弃 |

每个 Service 变化 → kube-proxy watch 到 → 刷新本机的规则。

### `pause` 3.10.1 (318KB)

**最小的容器镜像**，仅作为 Pod 的基础设施容器（infra container）：

```
Pod 创建
  → kubelet 先启动 pause 容器（持有 Pod 的 cgroup + namespace）
  → 再启动真正的业务容器，共享 pause 的 net/pid/ipc namespace
```

- PID 1 角色：回收僵尸进程（`wait4`）
- 体积仅 318KB，写在汇编/C 里，几乎没有逻辑
- 一个 Node 上有多少个 Pod 就有多少个 pause 容器

### `kindnetd` v20260213 (42.6MB)

这是 **kind** 项目自带的 CNI（网络插件），轻量级替代 Calico/Flannel：

- 每个节点分配一个 Pod CIDR（如 `10.244.0.0/24`）
- 通过 **host-local** 方式给 Pod 分配 IP
- 利用 `ip route` + Veth 实现跨节点 Pod 互通
- 直接操作 Linux 网络栈，不依赖额外的 overlay 或 BGP
- 适合 kind 这种单机/开发环境，**不用于生产**

---

## 存储组件

### `storage-provisioner` (gcr.io/k8s-minikube)

这是 **minikube 专用**的动态存储供应器：

- 监听 `PersistentVolumeClaim`（PVC）对象
- 当用户创建 PVC 时，自动在 minikube 虚拟机内创建对应的目录（hostPath）作为 PV
- 实现了最简单的 **Dynamic Provisioning**，开发测试用
- 生产环境中由 CSI Driver 替代（如 AWS EBS CSI、Ceph CSI 等）

---

## 组件间通信全景

```
用户 kubectl
    │
    ▼
┌─────────────┐   watch    ┌──────────────┐
│ kube-apiserver│◄─────────►│    etcd       │
└──────┬───────┘            └──────────────┘
       │
  ┌────┴────────────────────────┐
  ▼              ▼              ▼
scheduler    controller      kubelet
  │          manager            │
  │  (watch Pod/Node)           │  (watch Pod assigned to this node)
  │                             │
  │    assign Node              ▼
  │    ──────────►      ┌──────────────┐
  │                     │ pause (infra)│
  │                     └──────┬───────┘
  │                            │
  │                     ┌──────┴───────┐
  │                     │ 业务容器       │
  │                     └──────────────┘
  │
kube-proxy (watch Service/Endpoint)
  → iptables / ipvs 规则更新
  → 流量到达 Pod
```

---

## 关于镜像体积

| 镜像 | 大小 | 说明 |
|---|---|---|
| pause | 318KB | 汇编/C 写的，几乎无依赖 |
| 其他 Go 组件 | 17-43MB | 基于 `scratch` 或 `distroless` 静态编译 |
| kindnetd | 42.6MB | 稍大，包含完整网络工具链 |

所有 Kubernetes 核心组件都用 **Go 静态编译**，容器基础镜像是 `gcr.io/distroless/static` 或 `scratch`，所以体积都很小且没有 shell（除 debug 外）。

有什么具体组件想进一步深入？比如 etcd 的 Raft 协议细节、kube-proxy 的 iptables 规则链、或者调度器的插件框架？
