---
title: Cilium 底层细节 — 深度解析
date: 2026-09-07 12:45:00
tags:
  - Cilium
  - eBPF
  - CNI
  - Kubernetes
categories:
  - Kubernetes
---

# Cilium Underlying Details — Deep Dive

# Cilium 底层细节 — 深度解析

---

## 1. Cilium Architecture Overview

# 1. Cilium 架构总览

### 1.1 Component Map

```
┌──────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                              │
│                    Kubernetes 集群                                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  CONTROL PLANE                              │  │
│  │                  控制平面                                    │  │
│  │                                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │  │
│  │  │ Cilium       │  │ Cilium       │  │ Cilium       │     │  │
│  │  │ Operator     │  │ clustermesh  │  │ Hubble       │     │  │
│  │  │ (Deployment) │  │ (optional)   │  │ (optional)   │     │  │
│  │  │              │  │              │  │              │     │  │
│  │  │ - CRD mgmt   │  │ - Multi-     │  │ - Flow       │     │  │
│  │  │ - IPAM       │  │   cluster    │  │   observ.    │     │  │
│  │  │ - ENI/IPAM   │  │   networking │  │ - Metrics    │     │  │
│  │  │ - BGP peering│  │              │  │ - Service    │     │  │
│  │  │              │  │              │  │   Map        │     │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │  Kubernetes API Server                               │  │  │
│  │  │  - CiliumNetworkPolicy (CRD)                         │  │  │
│  │  │  - CiliumEndpoint (CRD)                              │  │  │
│  │  │  - CiliumNode (CRD)                                  │  │  │
│  │  │  - CiliumIdentity (CRD)                              │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  DATA PLANE (per node)                      │  │
│  │                  数据平面（每节点）                           │  │
│  │                                                            │  │
│  │  Node 1:                                                   │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │  Cilium Agent (DaemonSet)                            │  │  │
│  │  │                                                      │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │  │  │
│  │  │  │ K8s      │ │ eBPF     │ │ IPAM     │             │  │  │
│  │  │  │ Watcher  │ │ Datapath │ │ Manager  │             │  │  │
│  │  │  │          │ │ Manager  │ │          │             │  │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘             │  │  │
│  │  │                                                      │  │  │
│  │  │  Uses lib/bpf (gobpf) to:                           │  │  │
│  │  │  - Compile/load eBPF programs                        │  │  │
│  │  │  - Update BPF maps                                   │  │  │
│  │  │  - Attach programs to hooks                          │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │  Linux Kernel (eBPF programs running)                │  │  │
│  │  │                                                      │  │  │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐              │  │  │
│  │  │  │ TC hook │  │ XDP hook│  │ cgroup  │              │  │  │
│  │  │  │ (clsact)│  │ (ingress│  │ sock_ops│              │  │  │
│  │  │  │         │  │  only)  │  │         │              │  │  │
│  │  │  └─────────┘  └─────────┘  └─────────┘              │  │  │
│  │  │                                                      │  │  │
│  │  │  ┌───────────────────────────────────────────────┐   │  │  │
│  │  │  │  BPF Maps (shared between eBPF programs)      │   │  │  │
│  │  │  │                                               │   │  │  │
│  │  │  │  CT_MAP  │ POLICY_MAP │ SERVICE_MAP │ ...     │   │  │  │
│  │  │  └───────────────────────────────────────────────┘   │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. eBPF — The Engine Behind Cilium

# 2. eBPF — Cilium 背后的引擎

### 2.1 What Is eBPF?

```
eBPF (extended Berkeley Packet Filter) is a technology that allows
running sandboxed programs INSIDE the Linux kernel without modifying
the kernel source code or loading kernel modules.

eBPF（扩展伯克利数据包过滤器）是一种允许在 Linux 内核内部运行
沙盒程序的技术，无需修改内核源代码或加载内核模块。

┌──────────────────────────────────────────────────────────────┐
│                     User Space                                │
│                     用户空间                                   │
│                                                              │
│  ┌──────────────┐        ┌──────────────────────────────┐    │
│  │ Cilium Agent │        │    bpf() system call          │    │
│  │              │───────▶│    bpf() 系统调用              │    │
│  │ eBPF bytecode│        │                              │    │
│  │ (compiled    │        │  1. Load program              │    │
│  │  from C)     │        │     加载程序                   │    │
│  └──────────────┘        │  2. Verify (safety check)     │    │
│                          │     验证（安全检查）            │    │
│                          │  3. JIT compile to native     │    │
│                          │     JIT 编译为本地指令          │    │
│                          └──────────┬───────────────────┘    │
│                                     │                        │
│  ═══════════════════════════════════╪═══════════════════════ │
│                          Kernel Space│                        │
│                          内核空间    │                        │
│                                     ▼                        │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              eBPF Verifier                            │    │
│  │              eBPF 验证器                               │    │
│  │                                                      │    │
│  │  - No infinite loops (guaranteed termination)        │    │
│  │    无无限循环（保证终止）                               │    │
│  │  - No out-of-bounds memory access                    │    │
│  │    无越界内存访问                                      │    │
│  │  - All paths must be valid                           │    │
│  │    所有路径必须有效                                    │    │
│  │  - Max 1M instructions (kernel 5.2+)                 │    │
│  │    最大 100 万条指令（内核 5.2+）                      │    │
│  └──────────────────────────────────────────────────────┘    │
│                                     │                        │
│                                     ▼                        │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              JIT Compiler                             │    │
│  │              JIT 编译器                                │    │
│  │                                                      │    │
│  │  eBPF bytecode → native x86/ARM64 machine code       │    │
│  │  eBPF 字节码 → 原生 x86/ARM64 机器指令                │    │
│  │                                                      │    │
│  │  Performance: equivalent to kernel module code        │    │
│  │  性能：等同于内核模块代码                              │    │
│  └──────────────────────────────────────────────────────┘    │
│                                     │                        │
│                                     ▼                        │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Program Runs At Hook Point               │    │
│  │              程序在钩子点运行                           │    │
│  │                                                      │    │
│  │  XDP hook → TC hook → socket ops → cgroup hooks      │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 eBPF Program Types Used by Cilium

```
┌──────────────────────────────────────────────────────────────┐
│              eBPF Program Types in Cilium                     │
│              Cilium 中的 eBPF 程序类型                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. TC (Traffic Control) — clsact                            │
│     TC（流量控制）— clsact                                    │
│     ┌──────────────────────────────────────────────────┐     │
│     │ Hook: qdisc ingress/egress on each veth/eth      │     │
│     │ 钩子：每个 veth/eth 上的 qdisc 入站/出站          │     │
│     │ Direction: INGRESS + EGRESS                       │     │
│     │ 方向：入站 + 出站                                  │     │
│     │ Purpose: Pod networking, service DNAT, policy      │     │
│     │ 用途：Pod 网络、服务 DNAT、策略                     │     │
│     │ Priority: 1 (runs before other TC programs)        │     │
│     │ 优先级：1（在其他 TC 程序之前运行）                 │     │
│     └──────────────────────────────────────────────────┘     │
│                                                              │
│  2. XDP (eXpress Data Path)                                  │
│     XDP（快速数据路径）                                       │
│     ┌──────────────────────────────────────────────────┐     │
│     │ Hook: NIC driver level (before skb allocation)    │     │
│     │ 钩子：网卡驱动级别（在 skb 分配之前）               │     │
│     │ Direction: INGRESS only                            │     │
│     │ 方向：仅入站                                       │     │
│     │ Purpose: DDoS mitigation, service load balancing   │     │
│     │ 用途：DDoS 缓解、服务负载均衡                      │     │
│     │ Performance: FASTEST possible hook point           │     │
│     │ 性能：最快的钩子点                                 │     │
│     └──────────────────────────────────────────────────┘     │
│                                                              │
│  3. cgroup/sock_ops / cgroup/connect4/6                      │
│     ┌──────────────────────────────────────────────────┐     │
│     │ Hook: cgroup level socket operations              │     │
│     │ 钩子：cgroup 级别套接字操作                        │     │
│     │ Purpose: socket-level load balancing, host         │     │
│     │         firewall, socket-level policy              │     │
│     │ 用途：套接字级负载均衡、主机防火墙、套接字级策略    │     │
│     └──────────────────────────────────────────────────┘     │
│                                                              │
│  4. kprobe / tracepoint / perf_event                         │
│     ┌──────────────────────────────────────────────────┐     │
│     │ Hook: kernel function entry/exit, tracepoints     │     │
│     │ 钩子：内核函数入口/出口、跟踪点                    │     │
│     │ Purpose: observability (Hubble), debugging         │     │
│     │ 用途：可观测性（Hubble）、调试                     │     │
│     └──────────────────────────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Cilium Networking — The Data Path

# 3. Cilium 网络 — 数据路径

### 3.1 Node-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Physical Node                                                    │
│  物理节点                                                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Network Namespace: Host                                    │  │
│  │  网络命名空间：宿主机                                        │  │
│  │                                                            │  │
│  │  ┌──────────┐  eth0 (physical NIC)                         │  │
│  │  │ Physical │  192.168.1.10                                │  │
│  │  │   NIC    │  ◄── XDP program attached (optional)        │  │
│  │  │          │      XDP 程序已附加（可选）                    │  │
│  │  └────┬─────┘                                              │  │
│  │       │                                                    │  │
│  │       ▼                                                    │  │
│  │  ┌──────────────────────────────────────────────────┐      │  │
│  │  │  cilium_host (virtual interface)                  │      │  │
│  │  │  10.244.0.1/32 (node's pod CIDR gateway)         │      │  │
│  │  │  ◄── TC eBPF programs attached                    │      │  │
│  │  │      TC eBPF 程序已附加                            │      │  │
│  │  └──────────────────────────────────────────────────┘      │  │
│  │       │                                                    │  │
│  │       ▼                                                    │  │
│  │  ┌──────────────────────────────────────────────────┐      │  │
│  │  │  cilium_net (peer of cilium_host)                 │      │  │
│  │  │  ◄── TC eBPF programs attached (from-bpf overlay) │      │  │
│  │  └──────────────────────────────────────────────────┘      │  │
│  │                                                            │  │
│  │  Routing Table (installed by Cilium):                      │  │
│  │  路由表（由 Cilium 安装）：                                  │  │
│  │  10.244.0.0/24 via 10.244.0.1 dev cilium_host              │  │
│  │  10.244.1.0/24 via 192.168.1.11 dev eth0 (remote node)     │  │
│  │  10.244.2.0/24 via 192.168.1.12 dev eth0 (remote node)     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Pod 1 Network Namespace                                    │  │
│  │  Pod 1 网络命名空间                                          │  │
│  │                                                            │  │
│  │  ┌──────────────┐                                          │  │
│  │  │ eth0 (veth)  │  10.244.0.5/32                          │  │
│  │  │              │  ◄── TC eBPF programs attached            │  │
│  │  │              │      TC eBPF 程序已附加                    │  │
│  │  └──────┬───────┘                                          │  │
│  └─────────┼──────────────────────────────────────────────────┘  │
│            │                                                     │
│            │ veth pair                                            │
│            │                                                     │
│  ┌─────────┼──────────────────────────────────────────────────┐  │
│  │  Host Network Namespace                                      │  │
│  │  宿主机网络命名空间                                          │  │
│  │  ┌──────┴───────┐                                          │  │
│  │  │ lxcXXXXXX    │  (veth peer — Cilium names it this way)  │  │
│  │  │              │  veth 对端 — Cilium 如此命名               │  │
│  │  │              │  ◄── TC eBPF programs attached            │  │
│  │  │              │      TC eBPF 程序已附加                    │  │
│  │  └──────────────┘                                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Key Difference: Cilium vs kube-proxy

```
Traditional (kube-proxy + iptables):
传统方式（kube-proxy + iptables）：

  Pod → eth0 → bridge → routing table → iptables (DNAT)
        → conntrack → external network

  Every packet traverses the iptables rule chain
  每个数据包都遍历 iptables 规则链
  O(N) rule matching for N services
  对 N 个服务进行 O(N) 规则匹配


Cilium (eBPF replaces iptables + kube-proxy):
Cilium（eBPF 替代 iptables + kube-proxy）：

  Pod → eth0 (TC eBPF) → BPF map lookup (O(1)) → direct routing
        → external network

  NO iptables, NO conntrack kernel module
  无 iptables，无 conntrack 内核模块
  O(1) service lookup via BPF map
  通过 BPF map 进行 O(1) 服务查找

┌────────────────────────────────────────────────────────────┐
│                                                            │
│  iptables path:              eBPF path (Cilium):           │
│  iptables 路径：              eBPF 路径（Cilium）：          │
│                                                            │
│  Packet → PREROUTING         Packet → TC ingress BPF       │
│        → iptables rules            → BPF map lookup        │
│        → N services × M rules      → direct rewrite       │
│        → conntrack lookup           → forward              │
│        → DNAT                                                  │
│        → POSTROUTING                                         │
│        → out                                                  │
│                                                            │
│  Latency: higher              Latency: lower               │
│  延迟：更高                   延迟：更低                     │
│  Scaling: poor (>10k svc)    Scaling: excellent             │
│  扩展性：差（>10k 服务）     扩展性：优秀                    │
│  CPU overhead: high           CPU overhead: low             │
│  CPU 开销：高                 CPU 开销：低                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 3.3 Packet Walkthrough — Pod to Service (Same Node)

```
Source Pod (10.244.0.5) → Service ClusterIP (10.96.0.50:80)
→ Backend Pod (10.244.0.8:8000) on same node

Step-by-step:
逐步说明：

[1] Application calls connect(10.96.0.50, port 80)
    应用程序调用 connect(10.96.0.50, 端口 80)
        │
        ▼
[2] Socket created, kernel's TCP stack builds SYN packet:
    套接字创建，内核 TCP 协议栈构建 SYN 包：
    ┌─────────────────────────────────────────────┐
    │ Eth: dst=...  │ IP: dst=10.96.0.50 │ TCP: dport=80 │
    └─────────────────────────────────────────────┘
        │
        ▼
[3] Packet leaves Pod via eth0 → hits TC ingress eBPF on lxcXXXXXX
    数据包通过 eth0 离开 Pod → 命中 lxcXXXXXX 上的 TC 入站 eBPF
        │
        ▼
[4] Cilium bpf_lxc program runs:
    Cilium bpf_lxc 程序运行：
    
    ┌───────────────────────────────────────────────────────┐
    │ bpf_lxc (TC ingress on lxc device)                    │
    │                                                       │
    │ a) Look up source identity from source IP             │
    │    从源 IP 查找源身份                                   │
    │    BPF map: {10.244.0.5} → identity=1234              │
    │                                                       │
    │ b) Check: is destination a service ClusterIP?         │
    │    检查：目标是否是服务 ClusterIP？                     │
    │    BPF service map: {10.96.0.50:80} → backend list    │
    │    YES → perform service translation                  │
    │    是 → 执行服务转换                                   │
    │                                                       │
    │ c) Service load balancing (select backend):           │
    │    服务负载均衡（选择后端）：                            │
    │    Algorithm: Maglev consistent hashing               │
    │    算法：Maglev 一致性哈希                              │
    │    Selected: 10.244.0.8:8000                          │
    │                                                       │
    │ d) Rewrite packet headers:                            │
    │    重写数据包头部：                                     │
    │    - dst IP: 10.96.0.50 → 10.244.0.8                 │
    │    - dst port: 80 → 8000                              │
    │    - Recalculate IP checksum                          │
    │    - Recalculate TCP checksum                         │
    │                                                       │
    │ e) Policy check:                                      │
    │    策略检查：                                           │
    │    BPF policy map: {identity=1234, dst=12345,         │
    │                     port=8000, proto=TCP} → ALLOW     │
    │    ALLOW → continue                                   │
    │                                                       │
    │ f) Conntrack entry created:                           │
    │    创建 conntrack 条目：                               │
    │    BPF CT map: {10.244.0.5:ephemeral, 10.96.0.50:80} │
    │    → {10.244.0.5:ephemeral, 10.244.0.8:8000}         │
    │                                                       │
    │ g) Set packet destination, redirect to target device  │
    │    设置数据包目标，重定向到目标设备                      │
    └───────────────────────────────────────────────────────┘
        │
        ▼
[5] Packet redirected to cilium_host → routed to destination Pod
    数据包重定向到 cilium_host → 路由到目标 Pod
        │
        ▼
[6] Packet arrives at destination Pod's lxcYYYYYY → TC ingress eBPF
    数据包到达目标 Pod 的 lxcYYYYYY → TC 入站 eBPF
    
    bpf_lxc (ingress on dest lxc):
    - Conntrack lookup: is this a reply to existing connection?
      conntrack 查找：这是否是现有连接的回复？
    - Policy check: allow ingress?
      策略检查：允许入站？
    - FORWARD → deliver to Pod
      转发 → 传递到 Pod
        │
        ▼
[7] Destination Pod receives SYN packet
    目标 Pod 接收 SYN 数据包
```

---

## 4. BPF Maps — The Data Structures

# 4. BPF Map — 数据结构

### 4.1 Cilium's Key BPF Maps

```
┌──────────────────────────────────────────────────────────────────┐
│              Cilium BPF Maps (per node)                           │
│              Cilium BPF Map（每节点）                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CONNECTION TRACKING MAP (CT_MAP)                             │
│     连接跟踪表                                                    │
│     ┌──────────────────────────────────────────────────────┐     │
│     │ Type: HASH                                            │     │
│     │ 类型：哈希                                             │     │
│     │                                                      │     │
│     │ Key:                                                  │     │
│     │ ┌──────────────────────────────────────────────────┐ │     │
│     │ │ src_addr | dst_addr | src_port | dst_port | proto│ │     │
│     │ │  4 B     │  4 B     │  2 B     │  2 B     │ 1 B  │ │     │
│     │ └──────────────────────────────────────────────────┘ │     │
│     │                                                      │     │
│     │ Value:                                                │     │
│     │ ┌──────────────────────────────────────────────────┐ │     │
│     │ │ rx_bytes | tx_bytes | rx_packets | tx_packets    │ │     │
│     │ │ lifetime | flags | proxy_port | ...              │ │     │
│     │ └──────────────────────────────────────────────────┘ │     │
│     │                                                      │     │
│     │ Two maps: CT_MAP_TCP4 + CT_MAP_TCP6                 │     │
│     │ Two directions: TUPLE_F_IN + TUPLE_F_OUT            │     │
│     │ 两个方向：入站 + 出站                                  │     │
│     │                                                      │     │
│     │ Max entries: 1,000,000+ (configurable)               │     │
│     │ 最大条目数：1,000,000+（可配置）                       │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  2. SERVICE MAP (LB4_SERVICES_V2)                                │
│     服务映射表                                                    │
│     ┌──────────────────────────────────────────────────────┐     │
│     │ Type: HASH                                            │     │
│     │                                                      │     │
│     │ Key:                                                  │     │
│     │ ┌──────────────────────────────────────────────────┐ │     │
│     │ │ address | port | proto | scope | ...             │ │     │
│     │ │  4 B    │ 2 B  │ 1 B   │ 1 B   │                 │ │     │
│     │ └──────────────────────────────────────────────────┘ │     │
│     │                                                      │     │
│     │ Value:                                                │     │
│     │ ┌──────────────────────────────────────────────────┐ │     │
│     │ │ count (number of backends)                        │ │     │
│     │ │ backend_id_1, backend_id_2, ... backend_id_N      │ │     │
│     │ │ flags (SessionAffinity, LoadBalancer, NodePort)   │ │     │
│     │ └──────────────────────────────────────────────────┘ │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  3. SERVICE BACKEND MAP (LB4_BACKEND)                             │
│     服务后端映射表                                                 │
│     ┌──────────────────────────────────────────────────────┐     │
│     │ Key:   backend_id                                     │     │
│     │ Value: { address, port, proto, zone }                 │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  4. POLICY MAP (POLICY_MAP)                                      │
│     策略映射表                                                    │
│     ┌──────────────────────────────────────────────────────┐     │
│     │ Type: HASH                                            │     │
│     │                                                      │     │
│     │ Key:                                                  │     │
│     │ ┌──────────────────────────────────────────────────┐ │     │
│     │ │ identity (src/dest) | dport | proto | direction  │ │     │
│     │ └──────────────────────────────────────────────────┘ │     │
│     │                                                      │     │
│     │ Value:                                                │     │
│     │ ┌──────────────────────────────────────────────────┐ │     │
│     │ │ proxy_port (0=allow, >0=redirect to proxy)        │ │     │
│     │ │ auth_type | flags | ...                           │ │     │
│     │ └──────────────────────────────────────────────────┘ │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  5. ENDPOINT MAP (ENDPOINTS_MAP)                                  │
│     端点映射表                                                    │
│     ┌──────────────────────────────────────────────────────┐     │
│     │ Key:   ifindex (lxcXXXXXX interface index)            │     │
│     │ Value: { identity, flags, lxc_ifindex, ... }          │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  6. IDENTITY MAP (IDENTITY_MAP)                                   │
│     身份映射表                                                    │
│     ┌──────────────────────────────────────────────────────┐     │
│     │ Key:   identity (numeric ID)                          │     │
│     │ Value: { labels, label_hash }                         │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  7. ENCRYPT MAP (if IPsec/WireGuard enabled)                      │
│     加密映射表（如果启用了 IPsec/WireGuard）                       │
│     ┌──────────────────────────────────────────────────────┐     │
│     │ Key:   node CIDR or IP                                │     │
│     │ Value: SPI, key index, encrypt_key                    │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  8. NAT MAP (LB4_NAT) (for NodePort/ExternalTrafficPolicy)        │
│     NAT 映射表（用于 NodePort/ExternalTrafficPolicy）             │
│     ┌──────────────────────────────────────────────────────┐     │
│     │ Stores reverse NAT entries for return traffic         │     │
│     │ 存储返回流量的反向 NAT 条目                             │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 BPF Map Update Flow

```
When a Kubernetes Service is created:
当创建 Kubernetes Service 时：

[1] K8s API Server
    Service: llm-inference-svc (10.96.0.50:80)
    Endpoints: [10.244.0.5:8000, 10.244.0.8:8000]
        │
        ▼
[2] Cilium Agent watches via K8s informer
    Cilium Agent 通过 K8s informer 监听
        │
        ▼
[3] Cilium Agent translates to BPF map entries:
    Cilium Agent 翻译为 BPF map 条目：

    // Add backend entries
    // 添加后端条目
    bpf_map_update(LB4_BACKEND, 
      key=1, 
      value={addr=10.244.0.5, port=8000})

    bpf_map_update(LB4_BACKEND, 
      key=2, 
      value={addr=10.244.0.8, port=8000})

    // Add service entry pointing to backends
    // 添加指向后端的服务条目
    bpf_map_update(LB4_SERVICES_V2,
      key={addr=10.96.0.50, port=80, proto=TCP},
      value={count=2, backends=[1, 2], flags=...})

    // Update Maglev lookup table for consistent hashing
    // 更新 Maglev 查找表用于一致性哈希
    // (precomputed permutation table)
    // （预计算的置换表）
        │
        ▼
[4] All eBPF programs on this node immediately see updated maps
    此节点上的所有 eBPF 程序立即看到更新的 map
    Next packet → new lookup result (zero downtime!)
    下一个数据包 → 新的查找结果（零停机！）

Total time: < 100ms (compared to seconds/minutes for iptables)
总时间：< 100ms（相比之下 iptables 需要数秒/数分钟）
```

---

## 5. Identity-Based Security

# 5. 基于身份的安全

### 5.1 How Cilium Assigns Identities

```
┌──────────────────────────────────────────────────────────────────┐
│              Identity Assignment Process                          │
│              身份分配过程                                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Pod Labels:                                                     │
│  Pod 标签：                                                       │
│    app: llm-inference                                            │
│    version: v2                                                   │
│    env: production                                               │
│        │                                                         │
│        ▼                                                         │
│  Cilium Agent computes label hash:                               │
│  Cilium Agent 计算标签哈希：                                      │
│    hash("app=llm-inference:env=production:version=v2")           │
│        │                                                         │
│        ▼                                                         │
│  ┌──────────────────────────────────────────────────┐            │
│  │  Cilium Identity Store (distributed via CRD)      │            │
│  │  Cilium 身份存储（通过 CRD 分布）                   │            │
│  │                                                  │            │
│  │  CiliumIdentity CRD:                             │            │
│  │  ┌─────────────────────────────────────────────┐ │            │
│  │  │ apiVersion: cilium.io/v2                     │ │            │
│  │  │ kind: CiliumIdentity                         │ │            │
│  │  │ metadata:                                    │ │            │
│  │  │   name: 12345                                │ │            │
│  │  │ security-labels:                             │ │            │
│  │  │   app: llm-inference                         │ │            │
│  │  │   env: production                            │ │            │
│  │  │   version: v2                                │ │            │
│  │  │   k8s:io.cilium.k8s.namespace.labels: ...   │ │            │
│  │  └─────────────────────────────────────────────┘ │            │
│  │                                                  │            │
│  │  Identity 12345 → assigned to ALL pods with      │            │
│  │  these exact labels (across all nodes)            │            │
│  │  身份 12345 → 分配给所有具有这些                   │            │
│  │  标签的 Pod（跨所有节点）                           │            │
│  └──────────────────────────────────────────────────┘            │
│                                                                  │
│  KEY INSIGHT:                                                     │
│  关键洞察：                                                        │
│  - Identity is based on LABELS, not IPs                          │
│    身份基于标签，而非 IP                                           │
│  - Same identity across all nodes → policies are portable         │
│    跨所有节点的相同身份 → 策略是可移植的                            │
│  - Pod restart with new IP → same identity → same policy applies  │
│    Pod 重启后新 IP → 相同身份 → 策略仍然适用                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Policy Enforcement — The eBPF Way

```
CiliumNetworkPolicy YAML:
CiliumNetworkPolicy YAML：

apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: llm-inference-policy
spec:
  endpointSelector:
    matchLabels:
      app: llm-inference
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: api-gateway
      toPorts:
        - ports:
            - port: "8000"
              protocol: TCP

Cilium Agent processes this:
Cilium Agent 处理此策略：

[1] Watches CiliumNetworkPolicy via K8s informer
    通过 K8s informer 监听 CiliumNetworkPolicy
        │
        ▼
[2] Computes allowed source identities:
    计算允许的源身份：
    - Find all endpoints with label "app=api-gateway"
      查找所有具有标签 "app=api-gateway" 的端点
    - Get their identities: [6789, 7000, 7001]
      获取其身份：[6789, 7000, 7001]
        │
        ▼
[3] For each endpoint matching "app=llm-inference":
    对于每个匹配 "app=llm-inference" 的端点：
    
    Update its POLICY_MAP (BPF map on its veth):
    更新其 POLICY_MAP（其 veth 上的 BPF map）：

    bpf_map_update(POLICY_MAP,
      key={identity=6789, direction=INGRESS, dport=8000, proto=TCP},
      value={proxy_port=0, verdict=ALLOW})   // 0 = no proxy, allow
                                             // 0 = 不经代理，允许

    bpf_map_update(POLICY_MAP,
      key={identity=7000, direction=INGRESS, dport=8000, proto=TCP},
      value={proxy_port=0, verdict=ALLOW})

    // Default deny (implicit):
    // 默认拒绝（隐式）：
    // Any identity NOT in the map → packet dropped
    // 不在 map 中的任何身份 → 数据包被丢弃
        │
        ▼
[4] When a packet arrives at the endpoint's veth:
    当数据包到达端点的 veth 时：

    eBPF program bpf_lxc runs:
    eBPF 程序 bpf_lxc 运行：

    ┌─────────────────────────────────────────────────────┐
    │ // Pseudocode of the eBPF policy check              │
    │ // eBPF 策略检查的伪代码                              │
    │                                                     │
    │ src_identity = lookup_identity(src_ip)              │
    │ key = {                                             │
    │   identity: src_identity,                           │
    │   direction: INGRESS,                               │
    │   dport: packet.dst_port,                           │
    │   proto: packet.proto                               │
    │ }                                                   │
    │                                                     │
    │ entry = bpf_map_lookup_elem(POLICY_MAP, &key)       │
    │                                                     │
    │ if entry == NULL:                                   │
    │     return DROP   // No match = deny                │
    │                     // 无匹配 = 拒绝                 │
    │                                                     │
    │ if entry->proxy_port > 0:                           │
    │     // Redirect to L7 proxy (Envoy)                 │
    │     // 重定向到 L7 代理（Envoy）                      │
    │     return redirect_to_proxy(entry->proxy_port)     │
    │                                                     │
    │ if entry->verdict == ALLOW:                         │
    │     return FORWARD  // Allow packet through         │
    │                     // 允许数据包通过                  │
    └─────────────────────────────────────────────────────┘

Policy enforcement happens IN THE KERNEL at line rate!
策略在内核中以线路速率执行！
No user-space process involved for L3/L4 policies!
对于 L3/L4 策略不涉及用户空间进程！
```

---

## 6. Cilium Load Balancing (kube-proxy replacement)

# 6. Cilium 负载均衡（替代 kube-proxy）

### 6.1 Maglev Consistent Hashing

```
Cilium uses Maglev consistent hashing for service backend selection:
Cilium 使用 Maglev 一致性哈希进行服务后端选择：

┌──────────────────────────────────────────────────────────────────┐
│              Maglev Consistent Hashing                            │
│              Maglev 一致性哈希                                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Precomputation (done by Cilium Agent):                          │
│  预计算（由 Cilium Agent 完成）：                                  │
│                                                                  │
│  For each service, generate a lookup table of size M:            │
│  对于每个服务，生成大小为 M 的查找表：                            │
│                                                                  │
│  M = 65537 (default, prime number for uniformity)                │
│  M = 65537（默认，质数以实现均匀性）                              │
│                                                                  │
│  For each backend B_i:                                           │
│  对于每个后端 B_i：                                               │
│    permutation[i] = generate_permutation(B_i, M)                 │
│    使用两个哈希函数生成置换序列                                    │
│    (using two hash functions)                                    │
│                                                                  │
│  Build lookup table by interleaving permutations:                │
│  通过交错置换构建查找表：                                         │
│                                                                  │
│  Entry:  [0]    [1]    [2]    [3]    [4]    [5]    ...  [65536] │
│  Backend: B2    B1    B3    B2    B1    B3    ...    B1         │
│                                                                  │
│  This table is stored in a BPF map                               │
│  此表存储在 BPF map 中                                            │
│                                                                  │
│  To select backend for a connection:                             │
│  为连接选择后端：                                                  │
│    hash(src_ip, dst_ip, src_port, dst_port) % 65537              │
│    → index into lookup table → backend ID                        │
│    → 查找表索引 → 后端 ID                                        │
│                                                                  │
│  Properties:                                                     │
│  特性：                                                           │
│  - Consistent: same connection → always same backend             │
│    一致性：相同连接 → 始终相同后端                                 │
│  - Stable: adding/removing one backend → minimal disruption      │
│    稳定性：添加/移除一个后端 → 最小中断                           │
│    (only ~1/M connections reassign)                              │
│    （仅约 1/M 的连接重新分配）                                    │
│  - Uniform: even distribution across backends                    │
│    均匀性：后端之间均匀分布                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 XDP-Based Load Balancing (DSR Mode)

```
For maximum performance, Cilium can use XDP for service load balancing:
为了最大性能，Cilium 可以使用 XDP 进行服务负载均衡：

┌──────────────────────────────────────────────────────────────────┐
│              DSR (Direct Server Return) with XDP                  │
│              使用 XDP 的 DSR（直接服务器返回）                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Traditional NAT mode:                                           │
│  传统 NAT 模式：                                                  │
│                                                                  │
│  Client → LB Node → Backend Node → LB Node → Client              │
│  客户端 → LB 节点 → 后端节点 → LB 节点 → 客户端                   │
│          (DNAT)      (reply via       (SNAT)                     │
│                       LB node)                                   │
│  Problem: return traffic goes through LB node (double hop)       │
│  问题：返回流量经过 LB 节点（双重跳转）                           │
│                                                                  │
│  DSR mode (Cilium XDP):                                          │
│  DSR 模式（Cilium XDP）：                                         │
│                                                                  │
│  Client → LB Node ──────→ Backend Node                           │
│          (XDP encap      (decapsulate,                           │
│           in GUE/IPIP)    serve request)                         │
│                 ↑                                                 │
│  Client ←──────────────── Backend Node                           │
│          (reply directly to client,                              │
│           src IP = service VIP)                                  │
│  客户端 ←──────────────── 后端节点                                │
│          （直接回复客户端，源 IP = 服务 VIP）                      │
│                                                                  │
│  Benefit: only 1 hop for each direction = 50% bandwidth savings  │
│  优势：每个方向仅 1 跳 = 50% 带宽节省                             │
│                                                                  │
│  XDP code runs at NIC driver level:                              │
│  XDP 代码在网卡驱动级别运行：                                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  // XDP eBPF pseudocode for DSR                      │        │
│  │  // DSR 的 XDP eBPF 伪代码                            │        │
│  │                                                      │        │
│  │  int xdp_lb(struct xdp_md *ctx) {                    │        │
│  │      void *data = ctx->data;                         │        │
│  │      struct iphdr *ip = data + ETH_HLEN;             │        │
│  │                                                      │        │
│  │      // Lookup service in BPF map                    │        │
│  │      // 在 BPF map 中查找服务                         │        │
│  │      struct lb_service *svc =                        │        │
│  │          map_lookup_elem(&services, &ip->daddr);     │        │
│  │                                                      │        │
│  │      if (!svc) return XDP_PASS;                      │        │
│  │                                                      │        │
│  │      // Select backend via Maglev                    │        │
│  │      // 通过 Maglev 选择后端                          │        │
│  │      struct lb_backend *backend =                    │        │
│  │          select_backend(svc, ip, ...);               │        │
│  │                                                      │        │
│  │      // Encapsulate in GUE/IPIP                     │        │
│  │      // 封装在 GUE/IPIP 中                            │        │
│  │      encapsulate_gue(ip, backend->ip);               │        │
│  │                                                      │        │
│  │      // Rewrite dst MAC to backend                  │        │
│  │      // 重写目标 MAC 到后端                           │        │
│  │      rewrite_mac(ip, backend->mac);                  │        │
│  │                                                      │        │
│  │      return XDP_TX;  // Send it out fast!            │        │
│  │                       // 快速发出！                   │        │
│  │  }                                                   │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                  │
│  XDP performance:                                                │
│  XDP 性能：                                                       │
│  - Processes packets BEFORE they become sk_buff                  │
│    在数据包成为 sk_buff 之前处理                                   │
│  - Avoids memory allocation overhead                              │
│    避免内存分配开销                                                │
│  - Can achieve 10M+ packets/sec per core                         │
│    可实现每核心 1000 万+ 数据包/秒                                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 7. Cilium + WireGuard Encryption

# 7. Cilium + WireGuard 加密

```
┌──────────────────────────────────────────────────────────────────┐
│              Cilium Transparent Encryption                        │
│              Cilium 透明加密                                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Option 1: IPsec (strongSwan)                                    │
│  选项 1：IPsec（strongSwan）                                      │
│  - Uses XFRM kernel interfaces                                   │
│  - Per-node IPsec tunnels                                        │
│  - Higher CPU overhead                                           │
│  - CPU 开销更高                                                   │
│                                                                  │
│  Option 2: WireGuard (recommended)                               │
│  选项 2：WireGuard（推荐）                                        │
│  - Kernel-native (since Linux 5.6)                               │
│  - 内核原生（Linux 5.6 起）                                       │
│  - ChaCha20-Poly1305 encryption                                  │
│  - Very fast, minimal overhead                                   │
│  - 非常快，开销极小                                               │
│                                                                  │
│  Packet flow with WireGuard:                                     │
│  使用 WireGuard 的数据包流程：                                     │
│                                                                  │
│  Original packet from Pod:                                       │
│  来自 Pod 的原始数据包：                                           │
│  ┌──────────┬──────────┬──────────┬─────────┐                    │
│  │ Eth hdr  │ IP hdr   │ TCP hdr  │ Payload │                    │
│  │ src=pod  │ src=pod  │          │         │                    │
│  │ dst=next │ dst=ext  │          │         │                    │
│  └──────────┴──────────┴──────────┴─────────┘                    │
│       │                                                          │
│       ▼ (Cilium eBPF hooks the packet, routes to wg0)            │
│          （Cilium eBPF 钩接数据包，路由到 wg0）                    │
│                                                                  │
│  WireGuard encrypts and wraps:                                   │
│  WireGuard 加密并封装：                                           │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────────┐│
│  │ Outer Eth│ Outer IP │ UDP hdr  │ WG hdr   │ Encrypted        ││
│  │          │ src=this │ port=    │ (counter,│ inner packet     ││
│  │          │ node     │ 51820    │ receiver │ (ChaCha20 +      ││
│  │          │ dst=peer │          │ idx)     │  Poly1305)       ││
│  │          │ node     │          │          │                  ││
│  └──────────┴──────────┴──────────┴──────────┴──────────────────┘│
│       │                                                          │
│       ▼                                                          │
│  Transmitted over physical network                               │
│  通过物理网络传输                                                  │
│       │                                                          │
│       ▼ (Remote node receives, WireGuard decrypts)               │
│          （远程节点接收，WireGuard 解密）                          │
│       │                                                          │
│       ▼ (Cilium eBPF delivers to destination Pod)                │
│          （Cilium eBPF 传递到目标 Pod）                            │
│                                                                  │
│  Cilium WireGuard config per node:                               │
│  每节点的 Cilium WireGuard 配置：                                  │
│  - Creates wg0 interface                                         │
│    创建 wg0 接口                                                   │
│  - Key exchange via CiliumNode CRD                               │
│    通过 CiliumNode CRD 进行密钥交换                                │
│  - Automatically adds peer for each remote node                  │
│    自动为每个远程节点添加对等方                                     │
│  - Routes all pod-to-pod traffic through wg0                     │
│    将所有 Pod 到 Pod 的流量路由到 wg0                              │
│                                                                  │
│  Performance impact:                                             │
│  性能影响：                                                        │
│  - ~5-10% throughput reduction (vs unencrypted)                  │
│    约 5-10% 吞吐量降低（相比未加密）                               │
│  - ~1-2 μs additional latency                                    │
│    约 1-2 微秒额外延迟                                            │
│  - AES-NI hardware acceleration (ChaCha20 on ARM)                │
│    AES-NI 硬件加速（ARM 上的 ChaCha20）                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Hubble — Network Observability

# 8. Hubble — 网络可观测性

### 8.1 Hubble Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│              Hubble Architecture                                  │
│              Hubble 架构                                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Hubble UI (Deployment)                                  │    │
│  │  - Service dependency map                                │    │
│  │  - 服务依赖图                                             │    │
│  │  - Real-time flow visualization                          │    │
│  │  - 实时流量可视化                                         │    │
│  └──────────────────────┬───────────────────────────────────┘    │
│                         │ gRPC                                    │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Hubble Relay (Deployment)                               │    │
│  │  - Aggregates data from all Hubble instances             │    │
│  │  - 聚合所有 Hubble 实例的数据                              │    │
│  │  - Provides cluster-wide query API                       │    │
│  │  - 提供集群范围的查询 API                                  │    │
│  └──────────────────────┬───────────────────────────────────┘    │
│                         │ gRPC (peer service)                     │
│         ┌───────────────┼───────────────┐                        │
│         ▼               ▼               ▼                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│  │ Hubble     │  │ Hubble     │  │ Hubble     │                 │
│  │ (Node 1)   │  │ (Node 2)   │  │ (Node 3)   │                 │
│  │            │  │            │  │            │                 │
│  │ Embedded   │  │ Embedded   │  │ Embedded   │                 │
│  │ in Cilium  │  │ in Cilium  │  │ in Cilium  │                 │
│  │ Agent      │  │ Agent      │  │ Agent      │                 │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                 │
│        │               │               │                         │
│        ▼               ▼               ▼                         │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  eBPF Programs (kernel)                                  │    │
│  │                                                          │    │
│  │  Hubble observes packets by hooking into:                │    │
│  │  Hubble 通过钩接以下位置来观察数据包：                     │    │
│  │                                                          │    │
│  │  - bpf_lxc (TC hook on Pod veth)                        │    │
│  │    Pod veth 上的 TC 钩子                                  │    │
│  │  - bpf_overlay (overlay network)                         │    │
│  │    覆盖网络                                               │    │
│  │  - bpf_host (host network)                               │    │
│  │    主机网络                                               │    │
│  │  - cgroup/connect4 (socket-level)                        │    │
│  │    套接字级别                                             │    │
│  │                                                          │    │
│  │  Events are emitted to a perf ring buffer                │    │
│  │  事件被发送到 perf 环形缓冲区                              │    │
│  │  Hubble reads the ring buffer in user space              │    │
│  │  Hubble 在用户空间读取环形缓冲区                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 Flow Data Structure

```
Each observed flow (packet-level event) contains:
每个观察到的流量（数据包级事件）包含：

┌────────────────────────────────────────────────────────────┐
│  Hubble Flow (protobuf)                                    │
│                                                            │
│  {                                                         │
│    "time":     "2024-01-15T10:30:00.123Z",                │
│    "verdict":  "FORWARDED",          // or DROPPED         │
│                                      // 或 DROPPED         │
│    "drop_reason": 0,                                      │
│    "ethernet": {                                           │
│      "source":      "6a:bb:88:33:11:99",                  │
│      "destination": "6a:bb:88:33:11:aa"                   │
│    },                                                      │
│    "IP": {                                                 │
│      "source":      "10.244.0.5",                         │
│      "destination": "10.244.0.8",                         │
│      "ipVersion":   "IPv4"                                │
│    },                                                      │
│    "l4": {                                                 │
│      "TCP": {                                              │
│        "source_port":      48832,                         │
│        "destination_port": 8000                           │
│      }                                                     │
│    },                                                      │
│    "source": {                                             │
│      "ID":          1234,           // identity            │
│      "identity":    1234,                                 │
│      "namespace":   "default",                            │
│      "labels":      ["app=api-gateway"],                  │
│      "pod_name":    "api-gateway-5d9f8c7b6-x7k2m"        │
│    },                                                      │
│    "destination": {                                        │
│      "ID":          5678,                                 │
│      "identity":    5678,                                 │
│      "namespace":   "default",                            │
│      "labels":      ["app=llm-inference"],                │
│      "pod_name":    "llm-inference-pod-abc123"            │
│    },                                                      │
│    "Type":          "TRACE",                               │
│    "node_name":     "node-1",                             │
│    "event_type": {                                         │
│      "type": 5,                    // trace point type     │
│      "subType": 4                  // CT lookup            │
│    },                                                      │
│    "traffic_direction": "INGRESS",                         │
│    "summary": "TCP Flags: SYN"                             │
│  }                                                         │
└────────────────────────────────────────────────────────────┘
```

### 8.3 Hubble Prometheus Metrics

```
Hubble exports these metrics for Prometheus:
Hubble 导出以下 Prometheus 指标：

# Flow-level metrics
# 流量级指标
hubble_flows_processed_total{subsystem="dns"} 12345
hubble_flows_processed_total{subsystem="drop"} 67

# Drop metrics (very useful for debugging!)
# 丢弃指标（对调试非常有用！）
hubble_drop_total{
  reason="POLICY_DENIED",
  direction="INGRESS",
  verdict="DROPPED"
} 42

hubble_drop_total{
  reason="CT:INVALID",
  direction="EGRESS",
  verdict="DROPPED"
} 3

# DNS metrics
# DNS 指标
hubble_dns_total{
  qtypes="A",
  rcode="NOERROR",
  ips_returned="1"
} 5678

hubble_dns_total{
  qtypes="A",
  rcode="NXDOMAIN"
} 12

# TCP metrics
# TCP 指标
hubble_tcp_flags_total{
  flag="SYN",
  direction="INGRESS"
} 8901

hubble_tcp_flags_total{
  flag="RST",
  direction="EGRESS"
} 23    // RST flags may indicate connection issues
        // RST 标志可能表示连接问题
```

---

## 9. Cilium IPAM

# 9. Cilium IPAM（IP 地址管理）

```
┌──────────────────────────────────────────────────────────────────┐
│              Cilium IPAM Modes                                    │
│              Cilium IPAM 模式                                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Mode 1: CRD-based (default, on-premises)                        │
│  模式 1：基于 CRD（默认，本地部署）                                │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  Cilium Operator manages IP pools as CRDs            │        │
│  │  Cilium Operator 以 CRD 管理 IP 池                    │        │
│  │                                                      │        │
│  │  CiliumNode CRD:                                     │        │
│  │  spec:                                               │        │
│  │    ipam:                                             │        │
│  │      podCIDRs: ["10.244.0.0/24"]                     │        │
│  │      pool:                                           │        │
│  │        10.244.0.10: {}     # allocated               │        │
│  │        10.244.0.11: {}     # allocated               │        │
│  │        10.244.0.12: {}     # free                    │        │
│  │                                                      │        │
│  │  Cilium Agent requests IP for new pod:               │        │
│  │  Cilium Agent 为新 Pod 请求 IP：                       │        │
│  │  1. Look in local pool (fast path)                   │        │
│  │     在本地池中查找（快速路径）                           │        │
│  │  2. If empty → request from Operator                 │        │
│  │     如果为空 → 向 Operator 请求                        │        │
│  │  3. Operator allocates from CIDR, updates CRD        │        │
│  │     Operator 从 CIDR 分配，更新 CRD                    │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                  │
│  Mode 2: ENI (AWS)                                               │
│  模式 2：ENI（AWS）                                               │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  Cilium manages AWS ENIs directly                    │        │
│  │  Cilium 直接管理 AWS ENI                              │        │
│  │  - Attaches secondary ENIs to instances              │        │
│  │    将辅助 ENI 附加到实例                                │        │
│  │  - Allocates secondary IPs from ENI                  │        │
│  │    从 ENI 分配辅助 IP                                   │        │
│  │  - Uses AWS API for IP assignment                    │        │
│  │    使用 AWS API 进行 IP 分配                           │        │
│  │  - Pod IPs are VPC-routable (no overlay!)            │        │
│  │    Pod IP 可在 VPC 路由（无覆盖网络！）                │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                  │
│  Mode 3: Azure IPAM                                              │
│  模式 3：Azure IPAM                                               │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  Similar to ENI but uses Azure NICs                  │        │
│  │  类似 ENI，但使用 Azure NIC                            │        │
│  │  - Delegated NICs on Azure VMs                       │        │
│  │    Azure VM 上的委派 NIC                               │        │
│  │  - Pod IPs are Azure VNet-routable                   │        │
│  │    Pod IP 可在 Azure VNet 路由                         │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                  │
│  Mode 4: Multi-pool                                              │
│  模式 4：多池                                                     │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  Multiple IP pools with different CIDRs              │        │
│  │  多个不同 CIDR 的 IP 池                                │        │
│  │  - Pods can be assigned from different pools         │        │
│  │    Pod 可从不同池分配                                    │        │
│  │  - Useful for: dual-stack, isolation, routable pools │        │
│  │    适用于：双栈、隔离、可路由池                          │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 10. Cilium Tunnel vs Native Routing

# 10. Cilium 隧道模式 vs 原生路由模式

```
┌──────────────────────────────────────────────────────────────────┐
│  Mode 1: VXLAN Tunnel (default)                                  │
│  模式 1：VXLAN 隧道（默认）                                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Node A (192.168.1.10)        Node B (192.168.1.11)              │
│  ┌─────────────────┐         ┌─────────────────┐                │
│  │ Pod 10.244.0.5  │         │ Pod 10.244.1.8  │                │
│  └────────┬────────┘         └────────▲────────┘                │
│           │                           │                          │
│           │ eBPF                      │ eBPF                     │
│           ▼                           │                          │
│  ┌─────────────────┐         ┌────────┴────────┐                │
│  │ VXLAN encap     │         │ VXLAN decap     │                │
│  │                 │         │                 │                │
│  │ Outer:          │         │ Strip VXLAN hdr │                │
│  │  src=192.168.1.10│        │ Deliver to pod  │                │
│  │  dst=192.168.1.11│        │                 │                │
│  │  UDP:4789       │         │                 │                │
│  │ Inner:          │         │                 │                │
│  │  src=10.244.0.5 │         │                 │                │
│  │  dst=10.244.1.8 │         │                 │                │
│  └────────┬────────┘         └─────────────────┘                │
│           │                                                      │
│           │ Encapsulated packet over physical network            │
│           │ 封装数据包通过物理网络传输                             │
│           ▼                                                      │
│  Physical NIC → Switch → Physical NIC                            │
│                                                                  │
│  Pros: Works on ANY L3 network / 优点：适用于任何 L3 网络        │
│  Cons: 50 bytes overhead per packet / 缺点：每包 50 字节开销     │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Mode 2: Geneve Tunnel                                           │
│  模式 2：Geneve 隧道                                              │
│  - Similar to VXLAN                                              │
│  - Supports metadata extensions                                  │
│  - 支持元数据扩展                                                 │
│  - Used by AWS EKS with Cilium                                   │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Mode 3: Native Routing (no tunnel)                              │
│  模式 3：原生路由（无隧道）                                       │
│                                                                  │
│  Node A (192.168.1.10)        Node B (192.168.1.11)              │
│  ┌─────────────────┐         ┌─────────────────┐                │
│  │ Pod 10.244.0.5  │         │ Pod 10.244.1.8  │                │
│  └────────┬────────┘         └────────▲────────┘                │
│           │                           │                          │
│           │ eBPF (no encap)           │ eBPF                     │
│           ▼                           │                          │
│  ┌─────────────────┐         ┌────────┴────────┐                │
│  │ Route:          │         │ Receive packet   │                │
│  │ 10.244.1.0/24   │         │ with src IP      │                │
│  │ via 192.168.1.11│         │ 10.244.0.5       │                │
│  │ dev eth0        │         │ Deliver to pod   │                │
│  └────────┬────────┘         └─────────────────┘                │
│           │                                                      │
│           │ Native IP packet (no encapsulation)                  │
│           │ 原生 IP 数据包（无封装）                              │
│           ▼                                                      │
│  Physical NIC → Router/Switch → Physical NIC                     │
│                                                                  │
│  Requires: Network must route pod CIDRs                         │
│  要求：网络必须路由 Pod CIDR                                      │
│  Options:                                                        │
│  选项：                                                           │
│  - BGP peering (Cilium configures FRR/Kube-Router)              │
│    BGP 对等（Cilium 配置 FRR/Kube-Router）                       │
│  - Static routes on infrastructure router                        │
│    基础设施路由器上的静态路由                                      │
│  - AWS VPC native routing                                        │
│    AWS VPC 原生路由                                               │
│                                                                  │
│  Pros: No overhead, better performance                           │
│  优点：无开销，更好性能                                            │
│  Cons: Requires network support                                  │
│  缺点：需要网络支持                                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 11. Cilium eBPF Source Code Structure

# 11. Cilium eBPF 源代码结构

```
cilium/cilium repository:
cilium/cilium 代码仓库：

┌──────────────────────────────────────────────────────────────────┐
│  bpf/                          ← eBPF C source code              │
│  bpf/                            eBPF C 源代码                    │
│  ├── bpf_lxc.c                 ← Pod networking program          │
│  │                                Pod 网络程序                     │
│  ├── bpf_host.c                ← Host networking program         │
│  │                                主机网络程序                     │
│  ├── bpf_overlay.c             ← Tunnel/overlay program          │
│  │                                隧道/覆盖网络程序                │
│  ├── bpf_sock.c                ← Socket-level LB (sock_ops)      │
│  │                                套接字级负载均衡                 │
│  ├── bpf_xdp.c                 ← XDP load balancer               │
│  │                                XDP 负载均衡器                   │
│  │                                                              │
│  ├── lib/                      ← Shared eBPF library code        │
│  │   ├── conntrack.h             共享 eBPF 库代码                 │
│  │   ├── drop.h                  连接跟踪                         │
│  │   ├── lb.h                    丢弃处理                         │
│  │   ├── nat.h                   负载均衡                         │
│  │   ├── policy.h                NAT                              │
│  │   ├── trace.h                 策略                             │
│  │   └── encap.h                 跟踪                             │
│  │                                封装                             │
│  │                                                              │
│  ├── include/                  ← Header files                    │
│  │   ├── bpf/                    头文件                            │
│  │   └── linux/                                                  │
│  │                                                              │
│  └── Makefile                  ← Compiles .c → .o (BPF bytecode)│
│                                  编译 .c → .o（BPF 字节码）        │
│                                                                  │
│  pkg/                          ← Go source code (Cilium Agent)   │
│  pkg/                            Go 源代码（Cilium Agent）         │
│  ├── datapath/                 ← BPF program management          │
│  │   ├── linux/                  BPF 程序管理                     │
│  │   │   ├── config.go           编译/加载 BPF 程序               │
│  │   │   ├──邲_bpf.go            BPF map 初始化/更新              │
│  │   │   └── routes.go           路由管理                         │
│  │   └── types.go                                              │
│  │                                                              │
│  ├── k8s/                      ← Kubernetes watchers             │
│  │   ├── watcher.go              Kubernetes 监视器                │
│  │   ├── service.go              Service → BPF map translation   │
│  │   └── cilium_endpoint.go      CiliumEndpoint CRD management   │
│  │                                CiliumEndpoint CRD 管理        │
│  │                                                              │
│  ├── policy/                   ← Policy engine                   │
│  │   ├── repository.go           策略引擎                         │
│  │   ├── resolve.go              Policy → BPF map entries        │
│  │   └── distillery.go           策略 → BPF map 条目             │
│  │                                                              │
│  ├── endpoint/                 ← Endpoint (Pod) management       │
│  │   ├── manager.go              端点（Pod）管理                  │
│  │   └── bpf.go                  Per-endpoint BPF regeneration   │
│  │                                每端点 BPF 重生成               │
│  │                                                              │
│  ├── service/                  ← Service load balancing          │
│  │   ├── manager.go              服务负载均衡                     │
│  │   └── maglev.go               Maglev implementation           │
│  │                                Maglev 实现                     │
│  │                                                              │
│  ├── ipam/                     ← IP address management           │
│  │   ├── crd/                    IP 地址管理                      │
│  │   ├── aws/                    CRD, AWS ENI, Azure, Alibaba    │
│  │   ├── azure/                                              │
│  │   └── alibabacloud/                                       │
│  │                                                              │
│  └── hubble/                   ← Observability                   │
│      ├── parser/                 可观测性                         │
│      ├── metrics/                流量解析                         │
│      └── relay/                  指标                             │
│                                  中继                              │
│                                                                  │
│  operator/                     ← Cilium Operator                 │
│  operator/                       Cilium Operator                  │
│  ├── cmd/                      ← CRD management, IPAM, BGP      │
│  │                                CRD 管理、IPAM、BGP            │
│  └── ...                                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Summary — Cilium vs kube-proxy vs Calico

# 总结 — Cilium vs kube-proxy vs Calico

```
┌──────────────────┬───────────────┬──────────────┬───────────────┐
│ Feature          │ kube-proxy    │ Calico       │ Cilium        │
│ 特性             │ kube-proxy    │ Calico       │ Cilium        │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Data path        │ iptables      │ iptables/eBPF│ eBPF          │
│ 数据路径          │               │              │               │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Service LB       │ iptables      │ kube-proxy   │ eBPF (native) │
│ 服务负载均衡      │               │ still needed │ eBPF（原生）   │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Network Policy   │ N/A           │ iptables/eBPF│ eBPF (L3/L4)  │
│ 网络策略          │               │              │ + L7 (Envoy)  │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Encryption       │ N/A           │ WireGuard    │ WireGuard/IPsec│
│ 加密              │               │              │               │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Observability    │ conntrack only│ basic        │ Hubble (rich) │
│ 可观测性          │ 仅 conntrack  │ 基础         │ Hubble（丰富）│
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ L7 Policy        │ N/A           │ N/A          │ Yes (Envoy)   │
│ L7 策略          │               │              │ 是（Envoy）    │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Service Mesh     │ N/A           │ N/A          │ Yes (sidecar- │
│ 服务网格          │               │              │  less)        │
│                  │               │              │ 是（无边车）   │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ XDP LB           │ No            │ No           │ Yes           │
│ XDP 负载均衡      │ 否            │ 否           │ 是            │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Kernel required  │ Any           │ Any (3.x+)  │ 4.19+ (5.10+  │
│ 内核要求          │ 任何          │ 任何(3.x+)  │ recommended)  │
│                  │               │              │ 4.19+(推荐5.10│
│                  │               │              │ +)            │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Complexity       │ Low           │ Medium       │ High          │
│ 复杂度            │ 低            │ 中           │ 高            │
├──────────────────┼───────────────┼──────────────┼───────────────┤
│ Scale (services) │ Poor (>5k)    │ Medium       │ Excellent     │
│ 扩展性（服务数）  │ 差(>5k)       │ 中           │ 优秀          │
│                  │               │              │ (100k+ tested)│
│                  │               │              │ (已测试100k+) │
└──────────────────┴───────────────┴──────────────┴───────────────┘
```

Cilium's fundamental innovation is replacing the entire Linux networking stack (iptables, kube-proxy, conntrack, ipvs) with **eBPF programs** that run directly in the kernel, achieving **O(1) lookups**, **zero-copy forwarding**, **kernel-bypass policy enforcement**, and **rich observability** — all while maintaining full compatibility with the Kubernetes API.

Cilium 的根本创新是用直接运行在内核中的 **eBPF 程序**替代了整个 Linux 网络栈（iptables、kube-proxy、conntrack、ipvs），实现了 **O(1) 查找**、**零拷贝转发**、**内核旁路策略执行**和**丰富的可观测性** — 同时完全兼容 Kubernetes API。
