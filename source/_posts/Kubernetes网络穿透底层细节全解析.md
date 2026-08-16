---
title: Kubernetes 网络穿透 — 底层细节全解析
date: 2026-08-16 20:30:00
tags:
  - Kubernetes
  - 网络
  - CNI
  - kube-proxy
categories:
  - Kubernetes
---

## 一、流量完整路径总览

从外部请求到达 Pod 内部进程，数据包要穿越多个层次：

```
互联网用户
    │
    ▼
┌──────────────┐
│  物理/云负载均衡器 │ (SLB / NLB / MetalLB)
└──────┬───────┘
       │ NodePort 或 LoadBalancer 类型
       ▼
┌──────────────────────────────────────────┐
│  Node (宿主机)                            │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │ iptables / IPVS                     │  │
│  │ (kube-proxy 维护的规则)              │  │
│  └──────────────┬──────────────────────┘  │
│                 │ DNAT                    │
│                 ▼                          │
│  ┌─────────────────────────────────────┐  │
│  │ Linux Bridge / CNI 虚拟网桥          │  │
│  │ (cbr0 / cni0 / flannel.1 / ...)     │  │
│  └──────────────┬──────────────────────┘  │
│                 │ veth pair               │
│                 ▼                          │
│  ┌─────────────────────────────────────┐  │
│  │ Pod Network Namespace               │  │
│  │  eth0 → 进程监听端口                  │  │
│  └─────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

下面逐层剖析。

---

## 二、Service 网络穿透（南北流量）

### 1. ClusterIP 的底层实现

当创建一个 Service：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```

**kube-proxy 的工作**：

kube-proxy 有三种模式，底层实现完全不同：

#### a) iptables 模式（默认）

```bash
# kube-proxy 在每个节点上维护的 iptables 规则
# 手动查看：
iptables -t nat -L KUBE-SERVICES -n -v

# 实际生成的规则链（简化）：

# 1. 匹配 Service ClusterIP
-A KUBE-SERVICES -d 10.96.0.100/32 -p tcp --dport 80 \
  -j KUBE-SVC-XXXX

# 2. 如果有多个 Pod → 随机负载均衡（probability 模式）
-A KUBE-SVC-XXXX -m statistic --mode random --probability 0.33333333349 \
  -j KUBE-SEP-AAAA    # → Pod 1
-A KUBE-SVC-XXXX -m statistic --mode random --probability 0.50000000000 \
  -j KUBE-SEP-BBBB    # → Pod 2
-A KUBE-SVC-XXXX \
  -j KUBE-SEP-CCCC    # → Pod 3 (最后一个，100% 概率)

# 3. 每个 SEP（Service Endpoint）做 DNAT
-A KUBE-SEP-AAAA -p tcp -j DNAT --to-destination 10.244.1.5:8080
-A KUBE-SEP-BBBB -p tcp -j DNAT --to-destination 10.244.2.8:8080
-A KUBE-SEP-CCCC -p tcp -j DNAT --to-destination 10.244.3.2:8080
```

**数据包流经的完整内核路径**：

```
应用调用 connect(10.96.0.100:80)
    │
    ▼
TCP/IP 协议栈
    │
    ▼
PREROUTING 链 (iptables nat 表)
    │
    ▼
KUBE-SERVICES 链 ── 匹配 dst=10.96.0.100:80
    │
    ▼
KUBE-SVC-XXXX ── probability 随机选择后端
    │
    ▼
KUBE-SEP-AAAA ── DNAT: dst 10.96.0.100:80 → 10.244.1.5:8080
    │
    ▼
路由决策 (ip route)
    │
    ├─ 同节点 → 直接走 veth 到 Pod
    │
    └─ 跨节点 → 走 flannel/calico 封装
    │
    ▼
POSTROUTING 链 ── MASQUERADE（如果需要）
    │
    ▼
物理网卡 / 隧道接口发出
```

**iptables 模式的性能问题**：

```
规则数量 = Σ(每个 Service 的 Endpoint 数)

1000 个 Service，平均 10 个 Pod → 10,000+ 条 iptables 规则
每个新连接都需要线性遍历规则链
→ 大规模集群下，iptables 成为性能瓶颈
→ 规则更新时需要全量刷新（iptables-restore），瞬间卡顿
```

#### b) IPVS 模式

```bash
# 启用方式
kube-proxy --proxy-mode=ipvs --ipvs-scheduler=rr

# 底层使用内核的 IPVS（IP Virtual Server）模块
# 工作在 NETFILTER 的 LOCAL_IN / LOCAL_OUT 钩子

# 查看 IPVS 规则
ipvsadm -Ln

# 输出示例：
TCP  10.96.0.100:80 rr
  -> 10.244.1.5:8080     Masq    1      0
  -> 10.244.2.8:8080     Masq    1      0
  -> 10.244.3.2:8080     Masq    1      0
```

**IPVS vs iptables 核心区别**：

```
iptables:
  - 基于线性规则链匹配 → O(n)
  - 规则更新：全量重写 → 有瞬间中断
  - 仅支持随机负载均衡

IPVS:
  - 基于哈希表查找 → O(1)
  - 规则更新：增量操作 → 无中断
  - 支持多种调度算法：rr, lc, dh, sh, sed, nq...
  - 连接追踪在内核态完成，效率极高
```

#### c) nftables 模式（Kubernetes 1.29+ 实验性）

```bash
# nftables 是 iptables 的继任者
# 使用统一的 nf_tables 内核框架

# kube-proxy nftables 模式生成的规则：
nft list ruleset

table ip kube-proxy {
    chain services {
        ip daddr 10.96.0.100 tcp dport 80 \
          numgen random mod 3 vmap { 0 : goto ep-aaaa, 1 : goto ep-bbbb, 2 : goto ep-cccc }
    }
    chain ep-aaaa {
        dnat to 10.244.1.5:8080
    }
}
```

### 2. NodePort 穿透

```yaml
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080   # 范围默认 30000-32767
```

```bash
# iptables 额外规则：
# 所有节点的 30080 端口都被监听

-A KUBE-NODEPORTS -p tcp --dport 30080 \
  -j KUBE-EXT-XXXX

# 做 DNAT 到 Service ClusterIP（再走一次 Service 路由）
# 或直接 DNAT 到 Pod（取决于是否开启 externalTrafficPolicy）
```

**externalTrafficPolicy 区别**：

```
Cluster（默认）:
  客户端 → Node任意节点:30080 → DNAT到ClusterIP → DNAT到Pod
  缺点：多一跳，丢失源IP，跨节点转发可能

Local:
  客户端 → 有Pod的节点:30080 → 直接DNAT到本节点Pod
  优点：保留源IP，不跨节点
  缺点：如果某个节点没有该Pod，请求会丢弃
  底层：kube-proxy 在没有 Pod 的节点上不创建 DNAT 规则
```

### 3. LoadBalancer 穿透

```
云厂商 LB (SLB/NLB/ALB)
    │
    │  健康检查 → 直接检查 Node:NodePort
    │
    ▼
Node:30080 → iptables/IPVS → Pod

底层：
- 云控制器管理器 (CCM) 监听 Service 变更
- 调用云 API 创建负载均衡器
- 将所有节点的 NodePort 注册为后端
- BGP/ARP 通告 VIP（如果是 MetalLB）
```

---

## 三、Pod 间网络穿透（东西流量）

### 1. 同节点 Pod 通信

```
Pod A (10.244.0.5)                Pod B (10.244.0.8)
┌──────────────┐                  ┌──────────────┐
│  eth0        │                  │  eth0        │
└──────┬───────┘                  └──────┬───────┘
       │ veth-pair-A                     │ veth-pair-B
       │                                 │
┌──────┴─────────────────────────────────┴───────┐
│              cbr0 (Linux Bridge)                 │
│              或 cni0                              │
│              IP: 10.244.0.1                      │
└─────────────────────────────────────────────────┘

数据包路径：
Pod A eth0 → veth-pair-A → Bridge MAC表查询 → veth-pair-B → Pod B eth0

整个过程在内核态完成，不需要经过任何路由或封装
```

```bash
# 查看 veth pair 对应关系
ip link show type veth

# 查看 bridge 上连接的设备
brctl show cbr0
# 或
bridge link show

# 查看 Pod 的 network namespace
ls /var/run/docker/netns/   # Docker
ls /run/netns/               # 手动创建的
nsenter -t <pid> -n ip addr  # 进入容器网络命名空间查看
```

### 2. 跨节点 Pod 通信

这取决于 CNI 插件的实现，三种主流方案的底层完全不同：

#### a) Flannel (VXLAN 模式)

```
Node 1 (192.168.1.10)                    Node 2 (192.168.1.20)
┌───────────────────────┐                ┌───────────────────────┐
│ Pod: 10.244.0.5       │                │ Pod: 10.244.1.8       │
│        │              │                │        │              │
│     cbr0              │                │     cbr0              │
│        │              │                │        │              │
│    flannel.1          │                │    flannel.1          │
│   (VTEP: 10.244.0.0) │                │   (VTEP: 10.244.1.0) │
│        │              │                │        │              │
│   VXLAN 封装/解封装    │                │   VXLAN 封装/解封装    │
│        │              │                │        │              │
│     eth0              │                │     eth0              │
│  192.168.1.10         │                │  192.168.1.20         │
└───────────┬───────────┘                └───────────┬───────────┘
            │                                        │
            └──────── 物理网络/云 VPC ────────────────┘
```

**VXLAN 封装细节**：

```
原始数据包（Pod → Pod）:
┌──────────┬──────────┬───────────────────┐
│ Inner MAC│ Inner IP │    TCP/Payload     │
│ dst: Pod │dst:10.244.│                   │
│ MAC      │ 1.8      │                   │
└──────────┴──────────┴───────────────────┘

VXLAN 封装后:
┌──────────┬──────────┬───────────┬──────────┬──────────┬───────────────────┐
│Outer MAC │Outer IP  │  UDP:4789 │VXLAN HDR │Inner MAC │ Inner IP + Payload│
│dst: Node2│dst:192.168│           │ VNI: 1   │dst: Pod  │dst:10.244.1.8     │
│ MAC      │.1.20     │           │          │MAC       │                   │
└──────────┴──────────┴───────────┴──────────┴──────────┴───────────────────┘
```

```bash
# 查看 VXLAN 接口配置
ip -d link show flannel.1
# 输出：vxlan id 1 local 192.168.1.10 dev eth0 dstport 4789 nolearning

# 查看 FDB（Forwarding Database）— VTEP 到远端 IP 的映射
bridge fdb show dev flannel.1
# 输出：
# 00:00:00:00:00:00 dst 192.168.1.20 self permanent  ← 默认路由
# a6:3c:85:b2:xx:xx dst 192.168.1.20 self permanent  ← 远端 VTEP MAC

# 查看 ARP 表 — Pod IP 到 VTEP MAC 的映射
ip neigh show dev flannel.1
# 输出：
# 10.244.1.0 lladdr a6:3c:85:b2:xx:xx PERMANENT
```

#### b) Calico (BGP 模式)

```
Node 1 (192.168.1.10)                    Node 2 (192.168.1.20)
┌───────────────────────┐                ┌───────────────────────┐
│ Pod: 10.244.0.5       │                │ Pod: 10.244.1.8       │
│        │              │                │        │              │
│   caliXXX (veth)      │                │   caliYYY (veth)      │
│        │              │                │        │              │
│   路由表               │                │   路由表               │
│ 10.244.0.5 dev caliXXX│                │ 10.244.1.8 dev caliYYY│
│ 10.244.1.0/24 via     │                │ 10.244.0.0/24 via     │
│   192.168.1.20 dev eth0│               │   192.168.1.10 dev eth0│
│        │              │                │        │              │
│     eth0              │                │     eth0              │
│  192.168.1.10         │                │  192.168.1.20         │
└───────────┬───────────┘                └───────────┬───────────┘
            │                                        │
            └──────── BGP (Bird/FRR) 路由通告 ────────┘
```

```bash
# Calico 的路由表（每个节点上）
ip route show
# 10.244.0.5 dev cali1234 scope link        ← 本节点 Pod，直连
# 10.244.0.6 dev cali5678 scope link        ← 本节点 Pod，直连
# 10.244.1.0/24 via 192.168.1.20 dev eth0   ← 远端节点 Pod，BGP 学到的路由

# BGP 邻居状态
birdc show protocol
# bgp1  BGP  ...  up  ...  192.168.1.20  ← 与 Node2 建立的 BGP 邻居

# Calico 的 iptables 规则（策略执行）
iptables -t filter -L cali-FORWARD -n -v
# -A cali-FORWARD -i caliXXX -o caliYYY -j ACCEPT   ← 允许的 Pod 间通信
# -A cali-FORWARD -i caliXXX -o caliYYY -j DROP      ← 策略禁止的通信
```

**Calico vs Flannel 核心区别**：

```
Flannel VXLAN:
  - 每个数据包都被封装（overlay）
  - 额外开销：~50 bytes（UDP + VXLAN header）
  - 性能损失：5-15%
  - 对底层网络无要求（只要 IP 可达）

Calico BGP:
  - 不封装，纯三层路由
  - 零额外开销
  - 需要底层网络支持（同二层，或支持 BGP 的路由器）
  - 每个节点相当于一个路由器

Calico VXLAN（备选模式）:
  - 和 Flannel 一样用 VXLAN 封装
  - 但同时支持 NetworkPolicy
```

#### c) Cilium (eBPF 模式)

```
Node 1                              Node 2
┌───────────────────────┐          ┌───────────────────────┐
│ Pod: 10.244.0.5       │          │ Pod: 10.244.1.8       │
│        │              │          │        │              │
│   eth0 + BPF 程序     │          │   eth0 + BPF 程序     │
│   (TC ingress/egress) │          │   (TC ingress/egress) │
│        │              │          │        │              │
│  eBPF 转发决策         │          │  eBPF 转发决策         │
│  直接路由 / VXLAN      │          │  直接路由 / VXLAN      │
│        │              │          │        │              │
│     eth0              │          │     eth0              │
└───────────┬───────────┘          └───────────┬───────────┘
            │                                   │
            └───────── 物理网络 ─────────────────┘
```

```bash
# Cilium eBPF 内核态转发 — 绕过 iptables
# 查看 eBPF 程序挂载点
bpftool prog show

# 查看 eBPF map（存储 Service → Pod 映射）
bpftool map dump name cilium_lb4_services_v2
# Key:   {Service IP, Port, Backend ID}
# Value: {Pod IP, Pod Port, Flags}

# Cilium 的 kube-proxy 替代模式
# 完全在 eBPF 中完成 Service 的 DNAT + 负载均衡
# 不再需要 iptables/IPVS
cilium status --verbose
# kube-proxy-replacement: strict  ← 完全替代 kube-proxy
```

---

## 四、NetworkPolicy 穿透控制

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

**不同 CNI 的实现差异**：

```
Calico:
  iptables -A cali-tw-caliXXX -s 10.244.1.0/24 -p tcp --dport 80 -j ACCEPT
  iptables -A cali-tw-caliXXX -j DROP
  → 在目标 Pod 的 veth 设备上配置 iptables 规则

Cilium:
  eBPF 程序挂在 Pod 的 veth 的 TC (Traffic Control) 钩子上
  BPF map 存储策略规则
  → 内核态高效匹配，无需 iptables

Flannel:
  → 不支持 NetworkPolicy（需要加装 Calico 等）
```

---

## 五、Pod 与外部网络的穿透（Egress）

### SNAT（源地址转换）

```bash
# 当 Pod 访问外部网络时

Pod (10.244.0.5) → 访问 8.8.8.8
    │
    ▼
# iptables POSTROUTING 链
-A KUBE-POSTROUTING -m mark --mark 0x4000/0x4000 -j MASQUERADE

# SNAT: src 10.244.0.5 → src 192.168.1.10 (Node IP)
# 外部看到的是 Node 的 IP，看不到 Pod IP
```

### 避免 SNAT 的方案

```yaml
# 方案1: externalTrafficPolicy: Local
# 方案2: hostNetwork: true（Pod 直接使用 Node 网络栈）
# 方案3: Cilium eBPF 的 DSR (Direct Server Return)
```

---

## 六、DNS 穿透

```
Pod 内进程请求 my-service.default.svc.cluster.local
    │
    ▼
/etc/resolv.conf:
  nameserver 10.96.0.10      ← CoreDNS 的 ClusterIP
  search default.svc.cluster.local svc.cluster.local cluster.local
  ndots:5

    │
    ▼
iptables/IPVS → DNAT → CoreDNS Pod
    │
    ▼
CoreDNS 查询:
  1. 先查本地缓存
  2. 查 Kubernetes API (Informer cache)
  3. 返回 ClusterIP

# CoreDNS 底层使用 Kubernetes informer watch Service/Endpoint 变更
# 所有 DNS 记录都在内存中，不走外部 DNS
```

```bash
# 查看 CoreDNS 的 eBPF 加速（如果使用 Cilium）
# Cilium 可以在 eBPF 中直接处理 DNS，绕过 kube-proxy
cilium config | grep enable-local-dns
# enable-local-dns-agent: true
# Pod 的 DNS 请求被 eBPF 拦截，本地直接返回
```

---

## 七、完整数据包路径示例

```
场景: 外部用户 → Node A:30080 → Node B 上的 Pod

[物理层] 用户 → 云 LB → Node A eth0
          │
[内核入口] netfilter PREROUTING
          │
[iptables]  mangle/PREROUTING → nat/PREROUTING
          │                   匹配 dport=30080
          │                   DNAT → ClusterIP:80
          │
[路由]     本机路由 → ClusterIP 属于 Service CIDR
          │
[iptables]  nat/OUTPUT (如果是本机进程)
          │  nat/KUBE-SERVICES
          │  → KUBE-SVC-XXX → KUBE-SEP-YYY
          │  DNAT → 10.244.1.8:8080 (Pod在Node B)
          │
[路由]     10.244.1.0/24 via 192.168.1.20 (Calico BGP路由)
          │  或 通过 flannel.1 VXLAN 隧道
          │
[nat/POSTROUTING]  MASQUERADE (如果需要 SNAT)
          │
[内核出口]  eth0 → 物理网络 → Node B eth0
          │
[Node B]
[PREROUTING] → 路由 → 本地 Pod
          │
[caliXXX veth]  → eBPF/iptables 策略检查
          │
[Pod Network Namespace]
          │
[TCP]      应用进程 recv() 收到数据
```

---

## 八、关键性能数据

```
延迟对比（Pod → Pod，同节点）:
  bridge + iptables:  ~0.05ms
  Cilium eBPF:        ~0.02ms

延迟对比（Pod → Pod，跨节点）:
  Flannel VXLAN:      ~0.3ms (封装开销)
  Calico BGP:         ~0.1ms (无封装)
  Cilium eBPF+native: ~0.1ms

吞吐量（单连接 iperf3）:
  直连:               ~25 Gbps
  Calico BGP:         ~23 Gbps
  Flannel VXLAN:      ~18 Gbps
  Cilium eBPF:        ~23 Gbps

大规模集群 (5000 Service, 50000 Pod):
  iptables kube-proxy: 规则更新需 10s+, 期间丢包
  IPVS kube-proxy:     规则更新 <100ms
  Cilium eBPF:         规则更新 <10ms (增量map更新)
```

如果你想深入某个具体环节，比如 eBPF 内核态转发的实现、WireGuard 加密 overlay、或者 Service Mesh sidecar 的网络穿透，可以继续追问。
