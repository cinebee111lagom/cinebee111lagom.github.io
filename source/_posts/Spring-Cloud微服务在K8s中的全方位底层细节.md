---
title: Spring Cloud 微服务在 K8s 中的全方位底层细节
date: 2026-09-07 19:00:00
tags:
  - Spring Cloud
  - Kubernetes
  - 微服务
  - Pod
categories:
  - Kubernetes
---

## 一、Pod 创建的完整生命周期

当 `kubectl apply -f deployment.yaml` 执行后，K8s 内部发生了什么：

```
kubectl apply -f order-service-deployment.yaml
      │
      ▼
┌─── API Server ──────────────────────────────────────────┐
│                                                          │
│  1. 认证（Authentication）                               │
│     ├── 读取 ~/.kube/config 中的 client-certificate      │
│     ├── 或 ServiceAccount Token（Pod 内 kubectl）        │
│     └── 验证身份合法性                                    │
│                                                          │
│  2. 授权（Authorization）                                │
│     ├── RBAC 检查：该用户是否有 deployments/write 权限   │
│     └── ClusterRole → Role → RoleBinding 逐层匹配        │
│                                                          │
│  3. 准入控制（Admission Control）                         │
│     ├── MutatingWebhook：可能修改 Pod Spec               │
│     │   ├── 自动注入 Sidecar（如 Istio Envoy）           │
│     │   ├── 自动注入 SkyWalking Agent                    │
│     │   └── 注入 nodeAffinity / tolerations              │
│     │                                                    │
│     └── ValidatingWebhook：校验资源合法性                 │
│         ├── 镜像是否来自受信仓库                          │
│         ├── 资源 limits 是否合理                          │
│         └── 是否违反 OPA/Gatekeeper 策略                  │
│                                                          │
│  4. 持久化到 etcd                                        │
│     写入 Deployment 资源对象到 etcd                       │
│     key: /registry/deployments/microservice/order-service│
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌─── Controller Manager ──────────────────────────────────┐
│                                                          │
│  5. Deployment Controller 检测到变更                     │
│     对比 desired replicas (3) vs current (0)             │
│     需要创建 3 个 ReplicaSet                              │
│                                                          │
│  6. ReplicaSet Controller 创建 Pod                       │
│     为每个 Pod 生成唯一名称：                              │
│     order-service-7b5d8f6c9-abc12                        │
│     order-service-7b5d8f6c9-def34                        │
│     order-service-7b5d8f6c9-ghi56                        │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌─── Scheduler ───────────────────────────────────────────┐
│                                                          │
│  7. 为每个 Pod 选择运行节点                               │
│                                                          │
│     过滤阶段（Filter）：                                  │
│     ├── 节点资源是否充足（CPU/Memory）                    │
│     ├── 节点是否被 cordon（不可调度）                     │
│     ├── nodeSelector/nodeAffinity 是否匹配               │
│     ├── Pod 是否有 toleration 对应节点的 taint           │
│     ├── 拓扑分布约束（TopologySpreadConstraints）         │
│     └── CSI 卷是否能在该节点挂载                         │
│                                                          │
│     打分阶段（Score）：                                   │
│     ├── 资源均衡打分（资源利用率低的节点得分高）           │
│     ├── 亲和性/反亲和性打分                               │
│     ├── 拓扑分布打分（跨 zone 均匀分布）                  │
│     └── 最终选择得分最高的节点                            │
│                                                          │
│     绑定（Bind）：                                        │
│     将 Pod.nodeName 写入 etcd                             │
│     node: k8s-worker-03                                  │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌─── kubelet (目标节点) ──────────────────────────────────┐
│                                                          │
│  8. kubelet Watch 到新 Pod 被分配到本节点                 │
│                                                          │
│  9. 创建 Pod 沙箱（Sandbox）                             │
│     ├── 调用 CRI（Container Runtime Interface）          │
│     ├── 创建 Pause 容器（infra container）               │
│     │   ├── 创建 Network Namespace                       │
│     │   ├── 调用 CNI 插件分配 Pod IP                     │
│     │   │   ├── CNI 插件：Calico/Flannel/Cilium         │
│     │   │   ├── 分配 IP：10.244.3.15                     │
│     │   │   ├── 配置 veth pair                           │
│     │   │   └── 写入路由规则                              │
│     │   └── 设置 Pod 的 UTS/IPC/PID Namespace            │
│     └── Pause 容器成为所有业务容器的父容器                │
│                                                          │
│  10. 拉取镜像                                            │
│      ├── 检查本地是否有缓存                               │
│      ├── 如果 imagePullPolicy=IfNotPresent 且有缓存 → 跳过│
│      ├── 如果没有缓存，从 registry 拉取                   │
│      │   ├── 认证：读取 imagePullSecrets                 │
│      │   ├── 拉取 manifest → 按层下载 → 解压             │
│      │   └── 验证镜像签名（可选）                         │
│      └── 拉取完成后解压到本地存储                         │
│                                                          │
│  11. 按顺序启动容器                                      │
│      ├── 先启动 initContainers（如果有）                  │
│      │   ├── init-wait-nacos: 等待 Nacos 就绪            │
│      │   └── init-db-migration: 执行数据库迁移            │
│      └── 再启动主容器（containers）                       │
│          ├── order-service 容器                           │
│          └── sidecar 容器（如果有）                       │
│                                                          │
│  12. 容器启动后执行探针                                  │
│      ├── startupProbe → 等启动完成                       │
│      ├── readinessProbe → 就绪后加入 Service Endpoints   │
│      └── livenessProbe → 持续检查存活                    │
└──────────────────────────────────────────────────────────┘
```

---

## 二、Pod 内部的 Namespace 隔离细节

```
一个 Pod 内的所有容器共享以下 Namespace：

┌──────────────────────────────────────────────────────────┐
│  Pod: order-service-7b5d8f6c9-abc12                      │
│  IP: 10.244.3.15                                         │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ order-service    │  │ log-sidecar      │  ← 共享以下 │
│  │ (主容器)          │  │ (日志收集 Sidecar)│    命名空间  │
│  │                  │  │                  │             │
│  │ PID: 独立        │  │ PID: 独立        │  ← PID 不共享│
│  │                  │  │                  │             │
│  │ 共享:            │  │ 共享:            │             │
│  │ ├── Network NS ✓ │  │ ├── Network NS ✓ │  ← 同一个 IP│
│  │ ├── UTS NS ✓     │  │ ├── UTS NS ✓     │  ← 同一个主机名│
│  │ ├── IPC NS ✓     │  │ ├── IPC NS ✓     │  ← 可以进程间通信│
│  │ └── Mount NS ✗   │  │ └── Mount NS ✗   │  ← 各自独立的文件系统│
│  └──────────────────┘  └──────────────────┘             │
└──────────────────────────────────────────────────────────┘

含义：
├── 两个容器共享同一个 IP 地址和端口空间
├── order-service 监听 8080，sidecar 不能也监听 8080
├── 两个容器可以通过 localhost 互相通信
├── 两个容器共享 /dev/shm（共享内存）
└── 但各自有独立的文件系统（Mount Namespace）
```

**Java 应用在容器内的进程树：**

```bash
# 在 Pod 内执行 ps aux 看到的：

PID 1:  /pause                          # Pause 容器（infra container）
PID 7:  sh -c java $JAVA_OPTS -jar app.jar  # entrypoint wrapper
PID 8:  java -XX:+UseContainerSupport   # JVM 进程（实际的 Java 应用）
           -XX:MaxRAMPercentage=75.0
           -jar app.jar
PID 25: (java 内部) main thread         # Spring Boot 主线程
PID 26: (java 内部) tomcat-nio-8080     # Tomcat NIO 线程
PID 27: (java 内内) GC thread           # G1 GC 线程
PID 28: (java 内部) nacos-heartbeat     # Nacos 心跳线程
PID 29: (java 内部) sentinel-metrics    # Sentinel 统计线程
PID 30: (java 内部) hikari housekeeper  # HikariCP 连接池维护
...
```

---

## 三、K8s 网络在 Pod 级别的底层细节

### Pod 网络的 Linux 实现

```
Pod: order-service-7b5d8f6c9-abc12 (IP: 10.244.3.15)
所在节点: k8s-worker-03 (IP: 192.168.1.30)

节点内网络命名空间关系：

┌─────────────────────────────────────────────────────────┐
│  Host Network Namespace (k8s-worker-03)                 │
│  eth0: 192.168.1.30                                      │
│                                                          │
│  ┌────────────────────┐   ┌────────────────────┐       │
│  │ Pod A Network NS   │   │ Pod B Network NS   │       │
│  │ IP: 10.244.3.15    │   │ IP: 10.244.3.16    │       │
│  │                    │   │                    │       │
│  │ ┌────────────────┐ │   │ ┌────────────────┐ │       │
│  │ │ eth0 (veth)    │ │   │ │ eth0 (veth)    │ │       │
│  │ │ 10.244.3.15/24 │ │   │ │ 10.244.3.16/24 │ │       │
│  │ │ MTU: 1450      │ │   │ │ MTU: 1450      │ │       │
│  │ └───────┬────────┘ │   │ └───────┬────────┘ │       │
│  └─────────┼──────────┘   └─────────┼──────────┘       │
│            │                        │                   │
│     veth pair                veth pair                  │
│            │                        │                   │
│  ┌─────────▼────────────────────────▼──────────┐       │
│  │           cni0 / cbr0 (Linux Bridge)         │       │
│  │           10.244.3.1/24                      │       │
│  └─────────────────────┬───────────────────────┘       │
│                        │                                │
│  ┌─────────────────────▼───────────────────────┐       │
│  │           flannel.1 (VXLAN Interface)        │       │
│  │           VNI: 1                             │       │
│  └─────────────────────┬───────────────────────┘       │
│                        │                                │
│  ┌─────────────────────▼───────────────────────┐       │
│  │           eth0 (物理网卡)                     │       │
│  │           192.168.1.30                       │       │
│  └──────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

### Pod 内容器看到的网络配置

```bash
# 在 order-service 容器内执行：

# 网络接口
$ ip addr
1: lo: <LOOPBACK,UP,LOWER_UP>
    inet 127.0.0.1/8 scope host lo
2: eth0@if15: <BROADCAST,MULTICAST,UP,LOWER_UP>
    inet 10.244.3.15/24 scope global eth0   # Pod IP

# 路由表
$ ip route
default via 10.244.3.1 dev eth0            # 默认网关（cni0 bridge）
10.244.0.0/16 via 10.244.3.1 dev eth0      # 集群 Pod 网段
10.96.0.0/12 via 10.244.3.1 dev eth0       # 集群 Service 网段

# DNS 配置
$ cat /etc/resolv.conf
nameserver 10.96.0.10                      # CoreDNS
search microservice.svc.cluster.local svc.cluster.local cluster.local
ndots:5

# 主机名
$ hostname
order-service-7b5d8f6c9-abc12              # Pod 名称作为主机名
```

### Pod 到 Pod 跨节点通信的内核级细节

```
场景：order-service (Node A, 10.244.1.5) 调用 user-service (Node B, 10.244.2.8)

Node A (192.168.1.10)                         Node B (192.168.1.20)
┌───────────────────────┐                    ┌───────────────────────┐
│ Pod A 发送 TCP 数据    │                    │                       │
│ src: 10.244.1.5:49824 │                    │                       │
│ dst: 10.244.2.8:8080  │                    │                       │
│        │              │                    │                       │
│        ▼              │                    │                       │
│ 内核路由查找：         │                    │                       │
│ 10.244.2.8 不在本节点  │                    │                       │
│ → 需要通过 cni0 转发   │                    │                       │
│        │              │                    │                       │
│        ▼              │                    │                       │
│ ARP 查找 10.244.2.8   │                    │                       │
│ → flannel.1 知道      │                    │                       │
│ → 返回 flannel.1 的 MAC│                    │                       │
│        │              │                    │                       │
│        ▼              │                    │                       │
│ VXLAN 封装：           │                    │  VXLAN 解封装：        │
│ ┌──────────────────┐  │                    │  ┌──────────────────┐ │
│ │ Outer Eth Header │  │                    │  │ Outer Eth Header │ │
│ │ dst: Node B MAC  │  │                    │  │ (剥离)           │ │
│ ├──────────────────┤  │                    │  ├──────────────────┤ │
│ │ Outer IP Header  │  │                    │  │ Outer IP Header  │ │
│ │ src: 192.168.1.10│  │                    │  │ (剥离)           │ │
│ │ dst: 192.168.1.20│  │                    │  ├──────────────────┤ │
│ ├──────────────────┤  │                    │  │ UDP Header       │ │
│ │ UDP dst: 8472    │  │   物理网络          │  │ (剥离)           │ │
│ ├──────────────────┤  │  ──────────→       │  ├──────────────────┤ │
│ │ VXLAN Header     │  │                    │  │ VXLAN Header     │ │
│ │ VNI: 1           │  │                    │  │ (剥离，VNI=1)    │ │
│ ├──────────────────┤  │                    │  ├──────────────────┤ │
│ │ Inner Eth Header │  │                    │  │ Inner Eth Header │ │
│ │ dst: Pod B MAC   │  │                    │  │ dst: Pod B MAC   │ │
│ ├──────────────────┤  │                    │  ├──────────────────┤ │
│ │ Inner IP Packet  │  │                    │  │ Inner IP Packet  │ │
│ │ src: 10.244.1.5  │  │                    │  │ src: 10.244.1.5  │ │
│ │ dst: 10.244.2.8  │  │                    │  │ dst: 10.244.2.8  │ │
│ ├──────────────────┤  │                    │  ├──────────────────┤ │
│ │ TCP Segment      │  │                    │  │ TCP Segment      │ │
│ │ src port: 49824  │  │                    │  │ src port: 49824  │ │
│ │ dst port: 8080   │  │                    │  │ dst port: 8080   │ │
│ │ payload: HTTP    │  │                    │  │ payload: HTTP    │ │
│ └──────────────────┘  │                    │  └──────────────────┘ │
│                       │                    │          │            │
│                       │                    │          ▼            │
│                       │                    │ flannel.1 解封装     │
│                       │                    │ → 得到原始以太网帧    │
│                       │                    │ → 查 MAC 表          │
│                       │                    │ → 通过 veth pair     │
│                       │                    │ → 送达 Pod B 的 eth0 │
│                       │                    │          │            │
│                       │                    │          ▼            │
│                       │                    │ Pod B 的内核协议栈    │
│                       │                    │ → TCP 栈处理         │
│                       │                    │ → 放入 Socket 缓冲区 │
│                       │                    │ → Java read() 返回   │
└───────────────────────┘                    └──────────────────────┘
```

**MTU 的影响：**

```
物理网卡 MTU: 1500
VXLAN 封装额外开销: 50 bytes (14 outer eth + 20 outer IP + 8 UDP + 8 VXLAN)
Pod 内 MTU: 1450 (1500 - 50)

如果应用发送大于 1450 bytes 的数据：
  → 内核 TCP 栈根据 MSS (1450 - 40 TCP/IP header = 1410) 自动分片
  → 对应用完全透明
  → 但每个分片都有 VXLAN 封装开销，总体效率下降

优化方案：
├── 使用 Calico 的 IPIP 或 VXLAN 模式（可配置 MTU）
├── 使用 Cilium 的 eBPF 直接路由（无封装，性能最优）
└── 物理网络支持 Jumbo Frame（MTU 9000）→ Pod MTU 可设为 8950
```

---

## 四、Service 的 iptables/IPVS 底层

### ClusterIP Service 的内核实现

```yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
spec:
  type: ClusterIP
  clusterIP: 10.97.15.200
  ports:
    - port: 8080
      targetPort: 8080
  selector:
    app: user-service
```

**kube-proxy 在每个节点上创建的 iptables 规则：**

```bash
# kube-proxy 监听 Service 和 Endpoints 变更
# 发生变化时重写 iptables 规则

# 1. 在 nat 表中创建规则链
*nat
# Service 链
-A KUBE-SERVICES -d 10.97.15.200/32 -p tcp -m tcp --dport 8080 \
  -j KUBE-SVC-USER-SERVICE

# 负载均衡链（概率分流）
# 后端 Pod: 10.244.2.8, 10.244.2.9, 10.244.3.5
-A KUBE-SVC-USER-SERVICE \
  -m statistic --mode random --probability 0.33329999982 \
  -j KUBE-SEP-AAA  # → 10.244.2.8:8080

-A KUBE-SVC-USER-SERVICE \
  -m statistic --mode random --probability 0.49999999998 \
  -j KUBE-SEP-BBB  # → 10.244.2.9:8080

-A KUBE-SVC-USER-SERVICE \
  -j KUBE-SEP-CCC  # → 10.244.3.5:8080 (最后的直接走)

# DNAT 规则（目标地址转换）
-A KUBE-SEP-AAA -p tcp -m tcp --dport 8080 \
  -j DNAT --to-destination 10.244.2.8:8080

-A KUBE-SEP-BBB -p tcp -m tcp --dport 8080 \
  -j DNAT --to-destination 10.244.2.9:8080

-A KUBE-SEP-CCC -p tcp -m tcp --dport 8080 \
  -j DNAT --to-destination 10.244.3.5:8080
```

**数据包经过 iptables 的路径：**

```
Pod A (10.244.1.5) 发起连接到 ClusterIP 10.97.15.200:8080
      │
      ▼
内核 PREROUTING 链
      │
      ▼
nat 表 PREROUTING
  → 匹配 KUBE-SERVICES 规则
  → dst 10.97.15.200 匹配 KUBE-SVC-USER-SERVICE
  → 概率随机选择一个后端 Pod
  → 执行 DNAT：dst 改为 10.244.2.8:8080
      │
      ▼
路由决策
  → 原来目标是 ClusterIP（虚拟 IP）
  → DNAT 后目标变为真实 Pod IP
  → 路由查找：10.244.2.8 如何到达？
      │
      ▼
如果同节点：直接通过 cni0 bridge 送达
如果跨节点：通过 VXLAN 封装转发

回包时：
  Pod B 的响应 src=10.244.2.8, dst=10.244.1.5
  → conntrack 记录了 DNAT 映射
  → 内核自动做 SNAT：src 改回 10.97.15.200
  → Pod A 看到响应来自 ClusterIP，透明无感知
```

**为什么 Spring Cloud 直连 Pod IP 更高效：**

```
Spring Cloud 直连（Nacos 服务发现）：
  Pod A → Pod B (10.244.2.8:8080)
  不经过 ClusterIP，不经过 DNAT/SNAT
  路径更短，延迟更低，内核开销更小

通过 K8s Service：
  Pod A → ClusterIP (10.97.15.200:8080) → iptables DNAT → Pod B
  多了一层 NAT，conntrack 表有开销
  大规模集群下 conntrack 表可能成为瓶颈
```

### IPVS 模式（大规模集群推荐）

```bash
# 当 kube-proxy 以 IPVS 模式运行时
# 不使用 iptables，使用 Linux IPVS（IP Virtual Server）

# 查看 IPVS 规则
ipvsadm -Ln
# TCP  10.97.15.200:8080 rr
#   → 10.244.2.8:8080    Masq    1      0
#   → 10.244.2.9:8080    Masq    1      0
#   → 10.244.3.5:8080    Masq    1      0

# IPVS 支持多种负载均衡算法：
# rr  - Round Robin（轮询）
# wrr - Weighted Round Robin（加权轮询）
# lc  - Least Connection（最少连接）
# sh  - Source Hashing（源地址哈希，会话保持）
# dh  - Destination Hashing（目标地址哈希）
```

```
IPVS vs iptables 性能对比：

iptables:
  规则链式匹配：O(n)，规则越多越慢
  每个 Service 3-5 条规则
  10000 Service → 30000-50000 条 iptables 规则
  更新时需要全量重写所有规则

IPVS：
  哈希表查找：O(1)，性能恒定
  10000 Service → 10000 条 IPVS 规则
  支持增量更新
  支持更多负载均衡算法

结论：Service 数量 > 1000 时，IPVS 明显优于 iptables
```

---

## 五、Pod 调度的详细策略

### Spring Cloud 微服务推荐的调度配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 6
  template:
    spec:
      # ===== 1. 节点亲和性 =====
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            # 硬性要求：必须在有 ssd 标签的节点上
            nodeSelectorTerms:
              - matchExpressions:
                  - key: disk-type
                    operator: In
                    values: ["ssd"]
          preferredDuringSchedulingIgnoredDuringExecution:
            # 软性偏好：优先在高内存节点上
            - weight: 80
              preference:
                matchExpressions:
                  - key: node-type
                    operator: In
                    values: ["memory-optimized"]
        
        # ===== 2. Pod 反亲和性（跨节点分布） =====
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            # 硬性要求：同一个 order-service 的 Pod 不能在同一节点
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values: ["order-service"]
              topologyKey: kubernetes.io/hostname
          
          preferredDuringSchedulingIgnoredDuringExecution:
            # 软性偏好：尽量跨可用区分布
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values: ["order-service"]
                topologyKey: topology.kubernetes.io/zone
      
      # ===== 3. 拓扑分布约束 =====
      topologySpreadConstraints:
        - maxSkew: 1                          # 最大不均衡度
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule     # 不满足时拒绝调度
          labelSelector:
            matchLabels:
              app: order-service
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway    # 不满足时尽量满足
          labelSelector:
            matchLabels:
              app: order-service
      
      # ===== 4. 容忍度 =====
      tolerations:
        - key: "dedicated"
          operator: "Equal"
          value: "microservice"
          effect: "NoSchedule"          # 容忍专用节点的 taint
        - key: "node.kubernetes.io/not-ready"
          operator: "Exists"
          effect: "NoExecute"
          tolerationSeconds: 300         # 节点 NotReady 后 5 分钟才驱逐
      
      containers:
        - name: order-service
          resources:
            requests:
              memory: "512Mi"    # 调度依据：节点必须有 512Mi 可用
              cpu: "250m"        # 调度依据：节点必须有 0.25 核可用
            limits:
              memory: "1Gi"      # OOMKilled 阈值
              cpu: "1000m"       # CPU 限流阈值
```

**调度结果示例：**

```
6 个 Pod，3 个 Zone，每 Zone 2 个节点：

Zone A:
  Node A1: order-service-xxx-1 (CPU: 250m, Mem: 512Mi)
  Node A2: order-service-xxx-2 (CPU: 250m, Mem: 512Mi)

Zone B:
  Node B1: order-service-xxx-3 (CPU: 250m, Mem: 512Mi)
  Node B2: order-service-xxx-4 (CPU: 250m, Mem: 512Mi)

Zone C:
  Node C1: order-service-xxx-5 (CPU: 250m, Mem: 512Mi)
  Node C2: order-service-xxx-6 (CPU: 250m, Mem: 512Mi)

✓ 每个节点最多 1 个 Pod（反亲和性）
✓ 跨 3 个 Zone 均匀分布
✓ 单个 Zone 故障时，其他 Zone 继续服务
```

---

## 六、资源限制与 JVM 的精确配合

### cgroup 对 Java 进程的约束

```
K8s 创建 Pod 时，为每个容器创建 cgroup：

/sys/fs/cgroup/
├── memory/kubepods/
│   ├── burstable/
│   │   └── pod<uid>/
│   │       └── <container-id>/
│   │           ├── memory.limit_in_bytes   ← 1073741824 (1Gi)
│   │           ├── memory.usage_in_bytes   ← 当前内存使用
│   │           ├── memory.oom_control      ← OOM 控制
│   │           └── memory.stat             ← 详细内存统计
│   └── ...
├── cpu/kubepods/
│   ├── burstable/
│   │   └── pod<uid>/
│   │       └── <container-id>/
│   │           ├── cpu.cfs_quota_us        ← 100000 (=1核)
│   │           ├── cpu.cfs_period_us       ← 100000 (100ms)
│   │           ├── cpuacct.usage           ← 累计 CPU 时间(ns)
│   │           └── cpu.stat                ← throttling 统计
│   └── ...
└── ...
```

**JVM 如何感知 cgroup 限制：**

```java
// JDK 10+ (UseContainerSupport 默认开启)
// JVM 启动时读取 cgroup 文件

// 内存感知：
// 读取 /sys/fs/cgroup/memory/memory.limit_in_bytes
// 如果值 < 物理内存总量 → 认为运行在容器中
// 使用容器内存限制作为最大可用内存

// CPU 感知：
// 读取 /sys/fs/cgroup/cpu/cpu.cfs_quota_us 和 cpu.cfs_period_us
// availableProcessors = quota / period
// 如 quota=200000, period=100000 → availableProcessors=2

// 这直接影响：
// - GC 线程数（ParallelGCThreads = min(availableProcessors, 8)）
// - JIT 编译线程数
// - ForkJoinPool 线程数
// - Tomcat 默认线程数计算
```

**资源配比的常见问题：**

```
场景一：CPU 被限流（Throttling）

resources:
  requests:
    cpu: "100m"      # 请求 0.1 核
  limits:
    cpu: "200m"      # 限制 0.2 核

问题：Spring Cloud 应用启动时 CPU 需求很高
      （类加载、Bean 初始化、Nacos 注册）
      瞬时 CPU 超过 200m → 被内核限流
      → 启动变慢 → 可能超时 → livenessProbe 失败 → 重启

解决方案：
  方案一：启动时用 HPA 或 VPA 自动调整
  方案二：使用 Burstable QoS，limits 设高一些
  方案三：startupProbe 的 failureThreshold 设大
          给启动足够时间

场景二：内存 OOMKilled

resources:
  requests:
    memory: "512Mi"
  limits:
    memory: "512Mi"

JVM 参数:
  -Xmx400m
  -XX:MaxMetaspaceSize=128m

问题：400m (heap) + 128m (metaspace) + 线程栈 + 堆外 = 600m+
      超过 512Mi → OOMKilled

解决：limits.memory = MaxHeapSize × 1.5 ~ 2
      512Mi limit → -Xmx 最大 340m 左右
      或 limits.memory 设为 1Gi，heap 设为 600m

场景三：CPU Throttle 导致延迟毛刺

resources:
  requests:
    cpu: "500m"
  limits:
    cpu: "500m"

问题：requests == limits → Guaranteed QoS
      但 500m 在 GC 暂停后的突发请求中不够
      → GC 期间 CPU 被限流 → 响应延迟突增

监控指标：
  container_cpu_cfs_throttled_periods_total / 
  container_cpu_cfs_periods_total > 5% → 需要关注

解决：limits 设为 requests 的 2-3 倍
      允许短时突发
```

---

## 七、探针配置的精调

### Spring Boot 在 K8s 中的探针完整配置

```yaml
containers:
  - name: order-service
    image: registry.example.com/order-service:1.2.0
    
    # ===== 启动探针 =====
    # 解决 Spring Cloud 应用启动慢的问题
    startupProbe:
      httpGet:
        path: /actuator/health/liveness
        port: 8081              # management 端口
        httpHeaders:
          - name: Accept
            value: application/json
      initialDelaySeconds: 5    # 启动后 5 秒开始检测
      periodSeconds: 5          # 每 5 秒检测一次
      timeoutSeconds: 3         # 超时时间
      failureThreshold: 60      # 最大失败次数
      # 最长等待时间 = 5 + 5 × 60 = 305 秒
      # Spring Cloud 应用通常 60-120 秒启动完成
      # 启动探针成功前，liveness 和 readiness 不会执行
    
    # ===== 存活探针 =====
    # 检测进程是否还在正常运行
    livenessProbe:
      httpGet:
        path: /actuator/health/liveness
        port: 8081
      periodSeconds: 15         # 每 15 秒检测一次
      timeoutSeconds: 5
      failureThreshold: 3       # 连续 3 次失败 → 重启容器
      # 检测失败后的重启时间 = 15 × 3 = 45 秒
    
    # ===== 就绪探针 =====
    # 检测是否准备好接受流量
    readinessProbe:
      httpGet:
        path: /actuator/health/readiness
        port: 8081
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3       # 连续 3 次失败 → 从 Endpoints 摘除
      # 摘除时间 = 10 × 3 = 30 秒
```

**Spring Boot Actuator 探针端点的底层：**

```java
// liveness 探针：检查应用是否存活
// 默认检查的条件：
// - PingHealthIndicator（总是 UP）
// - 如果有 CAS 之类的组件也会检查

// readiness 探针：检查是否准备好接受流量
// 默认检查的条件：
// - DataSourceHealthIndicator（数据库连接是否正常）
// - RedisHealthIndicator（Redis 连接是否正常）
// - DiscoveryClientHealthIndicator（Nacos 是否注册成功）
// - RabbitHealthIndicator / KafkaHealthIndicator

// 当 readiness 探针返回 DOWN 时：
// → K8s 将该 Pod 从 Service Endpoints 中移除
// → 不再有新流量发送到该 Pod
// → 但已建立的 TCP 连接不受影响
// → Pod 内的进程继续运行

// 配置 readiness 探针包含哪些检查：
// application.yml
management:
  endpoint:
    health:
      probes:
        enabled: true
      group:
        readiness:
          include: "db,redis,nacos"   # 只检查这几个组件
        liveness:
          include: "ping"             # liveness 只需要 ping
```

**探针失败的连锁反应：**

```
场景：数据库连接池耗尽

1. readinessProbe 检查 DataSource
   → SELECT 1 超时 → health=DOWN
   → 连续 3 次失败 (30 秒)

2. K8s 将 Pod 从 Endpoints 摘除
   → 新流量不再路由到该 Pod
   → 但旧连接可能还在（长连接场景）

3. livenessProbe 检查 /actuator/health/liveness
   → 如果 liveness 只检查 ping → 仍然 UP → 不重启
   → 这是正确的！数据库问题是暂时的，不应杀掉进程

4. 数据库恢复后
   → readinessProbe 重新返回 UP
   → Pod 重新加入 Endpoints
   → 开始接收新流量

如果 liveness 也检查数据库：
   → liveness 也返回 DOWN
   → 连续 3 次 → K8s 重启容器
   → 重启后数据库可能还没恢复 → 又失败 → CrashLoopBackOff
   → 这就是为什么 liveness 和 readiness 要分开！
```

---

## 八、优雅停机的完整链路

当 K8s 决定停止一个 Pod（滚动更新、缩容、节点维护）时：

```
kubectl delete pod order-service-xxx-1
      │
      ▼
┌─── Step 1: Pod 状态变为 Terminating ────────────────────┐
│  Pod 从 Endpoints 中标记为删除                            │
│  （但可能有延迟，取决于 kube-proxy 的同步周期）             │
└──────────────────────────────────────────────────────────┘
      │
      ▼
┌─── Step 2: 执行 preStop Hook ───────────────────────────┐
│  lifecycle:                                              │
│    preStop:                                             │
│      exec:                                              │
│        command: ["sh", "-c", "sleep 10"]                │
│                                                          │
│  为什么需要 preStop sleep？                               │
│  因为 Step 1 的 Endpoints 更新可能有延迟（最长 10-30 秒）│
│  sleep 一段时间确保所有负载均衡器都已更新                  │
│  新流量不再到达这个 Pod                                   │
└──────────────────────────────────────────────────────────┘
      │
      ▼
┌─── Step 3: K8s 向容器内进程发送 SIGTERM ────────────────┐
│  PID 1 (Java 进程) 收到 SIGTERM                          │
│                                                          │
│  Spring Boot 的 ShutdownHook 被触发：                    │
│                                                          │
│  1. 发布 ContextClosedEvent                              │
│     → Nacos 取消注册                                     │
│     → 向 Nacos Server 发送 DELETE /nacos/v1/ns/instance  │
│     → 服务发现表中移除该实例                              │
│                                                          │
│  2. EmbeddedWebServer 停止                               │
│     → Tomcat 停止接收新连接                               │
│     → 等待正在处理的请求完成（最多 30 秒）                │
│     → 关闭 Executor 线程池                               │
│                                                          │
│  3. Bean 销毁                                            │
│     → HikariCP 连接池关闭（drain 连接）                  │
│     → Redis 连接关闭                                     │
│     → Nacos ConfigService 关闭（停止长轮询）              │
│     → RocketMQ Producer 关闭                             │
│                                                          │
│  4. ApplicationContext 关闭                               │
└──────────────────────────────────────────────────────────┘
      │
      ▼
┌─── Step 4: 等待 terminationGracePeriodSeconds ──────────┐
│  默认 30 秒                                              │
│  如果进程在此期间未自行退出 → 发送 SIGKILL 强制杀死       │
│                                                          │
│  对于 Spring Cloud 应用，建议设为 60 秒                   │
│  因为需要等待：                                           │
│  - 正在处理的请求完成（最长 30 秒）                       │
│  - 数据库事务提交或回滚                                   │
│  - Nacos 取消注册传播（其他客户端更新缓存需要时间）        │
│  - 连接池关闭                                             │
└──────────────────────────────────────────────────────────┘
```

**完整的时间线：**

```
T+0s:   kubectl scale deployment order-service --replicas=2
        （需要删除 1 个 Pod）

T+0s:   Pod 标记为 Terminating
        Pod 从 Endpoints 中移除（标记删除）

T+0s:   preStop 开始执行 → sleep 10

T+10s:  preStop 结束
        kube-proxy / 各客户端的 LoadBalancer 已更新
        此时不应该有新请求到达

T+10s:  SIGTERM 发送给 JVM
        Spring ShutdownHook 开始执行
        Nacos 取消注册 → 其他服务的缓存开始更新

T+11s:  Tomcat 停止接受新连接
        已有的请求继续处理中

T+15s:  最后一个请求处理完成
        Tomcat 线程池关闭

T+16s:  HikariCP 连接池关闭
        Redis 连接关闭

T+17s:  ApplicationContext 完全关闭
        JVM 进程退出 (exit code 143 = 128 + 15 SIGTERM)

T+17s:  容器停止，Pod 删除完成
```

**Spring Boot 优雅停机配置：**

```yaml
server:
  shutdown: graceful              # 启用优雅停机

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s  # 每个阶段最长等待时间

# Tomcat 停止后的处理
management:
  endpoint:
    shutdown:
      enabled: true               # 暴露 /actuator/shutdown 端点
```

---

## 九、ConfigMap 和 Secret 的挂载与热更新

### 挂载方式的底层差异

```yaml
# 方式一：环境变量注入（不支持热更新）
env:
  - name: SPRING_DATASOURCE_URL
    valueFrom:
      configMapKeyRef:
        name: common-config
        key: datasource-url
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-secret
        key: password

# 方式二：Volume 挂载（支持热更新）
volumeMounts:
  - name: app-config
    mountPath: /app/config
    readOnly: true
  - name: tls-certs
    mountPath: /app/certs
    readOnly: true
volumes:
  - name: app-config
    configMap:
      name: order-service-config
      items:
        - key: application.yaml
          path: application.yaml     # 挂载为文件
  - name: tls-certs
    secret:
      secretName: order-tls
```

**Volume 挂载的底层实现：**

```
K8s ConfigMap 挂载到 Pod 的过程：

1. kubelet Watch 到 Pod 使用了 configMap volume
2. kubelet 从 API Server 获取 ConfigMap 内容
3. kubelet 在节点上创建目录：
   /var/lib/kubelet/pods/<pod-uid>/volumes/kubernetes.io~configmap/app-config/
4. 将 ConfigMap 的每个 key 写为文件：
   /var/lib/kubelet/pods/<pod-uid>/volumes/.../app-config/application.yaml
5. 使用 bind mount 将该目录挂载到容器的 /app/config/
6. 容器内读取 /app/config/application.yaml → 实际读取的是节点上的文件

热更新机制：
  当 ConfigMap 被修改后：
  kubelet 检测到变更（Watch API Server）
  → 更新节点上的文件（原子替换）
  → 容器内的 /app/config/application.yaml 自动变化
  → 应用如果监控了该文件变化，可以热加载

  但：更新延迟 1-2 分钟（取决于 kubelet 的 sync 频率）
  且：不会触发 Spring 的 @RefreshScope 重新初始化
```

**将 Nacos 配置与 ConfigMap 结合使用的方案：**

```yaml
# bootstrap.yml 通过 ConfigMap 挂载
# 包含 Nacos 连接信息（不包含业务配置）
apiVersion: v1
kind: ConfigMap
metadata:
  name: order-service-bootstrap
data:
  bootstrap.yml: |
    spring:
      application:
        name: order-service
      cloud:
        nacos:
          config:
            server-addr: ${NACOS_ADDR}
            namespace: ${NAMESPACE}
            file-extension: yaml
            shared-configs:
              - data-id: common-datasource.yaml
                group: SHARED_GROUP
                refresh: true
          discovery:
            server-addr: ${NACOS_ADDR}
            namespace: ${NAMESPACE}
```

---

## 十、日志与可观测性在 K8s 中的细节

### 日志收集架构

```
┌──────────────────────────────────────────────────────────┐
│  Pod: order-service                                      │
│                                                          │
│  ┌──────────────────┐   ┌──────────────────┐           │
│  │ order-service    │   │ filebeat-sidecar │           │
│  │ (主容器)          │   │ (日志收集)        │           │
│  │                  │   │                  │           │
│  │ stdout → ────────┼──→│ 读取 stdout      │           │
│  │ stderr → ────────┼──→│ 读取 stderr      │           │
│  │                  │   │                  │           │
│  │ /app/logs/ ──────┼──→│ 读取日志文件      │           │
│  │  ├── app.log     │   │                  │           │
│  │  ├── gc.log      │   │ 推送到 ES/Kafka  │           │
│  │  └── access.log  │   │                  │           │
│  └──────────────────┘   └──────────────────┘           │
│                                                          │
│  或者使用 EmptyDir 共享日志：                              │
│  两个容器挂载同一个 emptyDir volume                       │
│  order-service 写入日志 → filebeat 读取                   │
└──────────────────────────────────────────────────────────┘

节点级别的日志路径：
/var/log/pods/<namespace>_<pod-name>_<pod-uid>/
├── <container-name>/
│   ├── 0.log        ← stdout
│   ├── 1.log        ← stderr
│   └── 2.log        ← 旧日志轮转
```

**Java 应用日志输出到 stdout 的配置：**

```xml
<!-- logback-spring.xml -->
<configuration>
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <!-- K8s 日志系统需要 JSON 格式才能结构化解析 -->
            <pattern>{"timestamp":"%d{yyyy-MM-dd'T'HH:mm:ss.SSS'Z'}", 
                     "level":"%level", 
                     "thread":"%thread", 
                     "traceId":"%X{traceId:-}", 
                     "spanId":"%X{spanId:-}", 
                     "logger":"%logger{36}", 
                     "msg":"%msg", 
                     "service":"${SERVICE_NAME:-unknown}", 
                     "pod":"${POD_NAME:-unknown}"}</pattern>
        </encoder>
    </appender>
    
    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
    </root>
</configuration>
```

### SkyWalking Agent 无侵入接入

```yaml
# 通过 initContainer 注入 SkyWalking Java Agent
initContainers:
  - name: skywalking-agent
    image: apache/skywalking-java-agent:9.0.0-java21
    command: ['sh', '-c', 'cp -r /agent /skywalking-agent']
    volumeMounts:
      - name: skywalking-agent
        mountPath: /skywalking-agent

containers:
  - name: order-service
    env:
      - name: JAVA_TOOL_OPTIONS
        value: >-
          -javaagent:/skywalking-agent/skywalking-agent.jar
          -Dskywalking.agent.service_name=order-service
          -Dskywalking.collector.backend_service=skywalking-oap.middleware:11800
          -Dskywalking.agent.instance_name=$(POD_NAME)
    volumeMounts:
      - name: skywalking-agent
        mountPath: /skywalking-agent
        readOnly: true

volumes:
  - name: skywalking-agent
    emptyDir: {}
```

---

## 十一、HPA 自动扩缩容的底层

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-service
  minReplicas: 3
  maxReplicas: 20
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60    # 扩容稳定窗口
      policies:
        - type: Pods
          value: 4                      # 每次最多扩 4 个 Pod
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300   # 缩容稳定窗口（更保守）
      policies:
        - type: Percent
          value: 10                     # 每次最多缩 10%
          periodSeconds: 60
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60        # CPU 平均利用率 60% 时扩容
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods                       # 自定义指标
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"          # 每个 Pod 1000 QPS 时扩容
```

**HPA 的工作循环（每 15 秒）：**

```
Metrics Server 收集各 Pod 的 CPU/Memory 指标
      │
      ▼
HPA Controller 每 15 秒执行一次评估：

1. 获取当前指标
   order-service 的 6 个 Pod：
   Pod1: CPU 70%, Mem 65%
   Pod2: CPU 80%, Mem 70%
   Pod3: CPU 55%, Mem 60%
   Pod4: CPU 75%, Mem 68%
   Pod5: CPU 90%, Mem 75%
   Pod6: CPU 85%, Mem 72%

2. 计算期望副本数
   CPU: 平均利用率 = (70+80+55+75+90+85)/6 = 75.8%
   目标: 60%
   期望副本数 = ceil(6 × 75.8/60) = ceil(7.58) = 8

   Memory: 平均利用率 = (65+70+60+68+75+72)/6 = 68.3%
   目标: 70%
   68.3% < 70% → 不需要扩容
   期望副本数 = 6

3. 取最大值
   max(8, 6) = 8

4. 检查 behavior 规则
   scaleUp 每次最多扩 4 个 Pod
   从 6 扩到 8 → 扩 2 个 → 没超过 4 → 允许

5. 执行扩容
   kubectl scale deployment order-service --replicas=8
```

**自定义指标接入 HPA：**

```java
// 应用暴露自定义指标到 Prometheus
@Component
public class RequestMetrics {
    
    private final AtomicInteger activeRequests = new AtomicInteger(0);
    
    // 使用 Micrometer 暴露指标
    @Bean
    public MeterBinder httpRequestsGauge() {
        return registry -> Gauge.builder("http_requests_per_second", 
                activeRequests, AtomicInteger::doubleValue)
            .register(registry);
    }
}

// Prometheus Adapter 将指标转为 K8s Custom Metrics API
// HPA 通过 Custom Metrics API 查询该指标
```

---

## 十二、NetworkPolicy（网络策略）细节

```yaml
# 限制 order-service 只能被 gateway 和同 namespace 的服务访问
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: order-service-netpol
  namespace: microservice
spec:
  podSelector:
    matchLabels:
      app: order-service
  policyTypes:
    - Ingress    # 入方向规则
    - Egress     # 出方向规则
  
  ingress:
    # 只允许来自 gateway 的流量
    - from:
        - podSelector:
            matchLabels:
              app: gateway
      ports:
        - port: 8080
          protocol: TCP
    
    # 允许同 namespace 的服务访问
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: microservice
      ports:
        - port: 8080
          protocol: TCP
    
    # 允许 Prometheus 抓取指标
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - port: 8081
          protocol: TCP
  
  egress:
    # 允许访问数据库
    - to:
        - ipBlock:
            cidr: 10.0.5.0/24      # 数据库网段
      ports:
        - port: 3306
          protocol: TCP
    
    # 允许访问 Nacos
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: middleware
          podSelector:
            matchLabels:
              app: nacos
      ports:
        - port: 8848
          protocol: TCP
        - port: 9848
          protocol: TCP    # gRPC
    
    # 允许 DNS 查询（必须）
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP
    
    # 允许访问其他微服务
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: microservice
      ports:
        - port: 8080
          protocol: TCP
```

**NetworkPolicy 的底层实现（以 Calico 为例）：**

```
Calico 的 Felix Agent 在每个节点上：
  → Watch API Server 的 NetworkPolicy 变更
  → 转换为 iptables / eBPF 规则
  → 写入节点的网络过滤规则

order-service Pod 的 iptables 规则：
-A cali-tw-cali1234 -s 10.244.0.10/32 -p tcp --dport 8080 -j ACCEPT  # gateway
-A cali-tw-cali1234 -s 10.244.0.0/16 -p tcp --dport 8080 -j ACCEPT   # 同namespace
-A cali-tw-cali1234 -j DROP                                           # 其他全部拒绝
```

---

## 十三、Secret 管理的最佳实践

```yaml
# K8s Secret 的存储是 base64 编码，不是加密！
# etcd 中存储的 Secret 需要加密配置

# etcd 加密配置（API Server 层面）：
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}  # 回退到明文（读取旧数据）
```

**Spring Cloud 应用获取 Secret 的方式：**

```yaml
# 方式一：通过环境变量（最简单但不够灵活）
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-secret
        key: password

# 方式二：通过 Volume 挂载为文件
volumeMounts:
  - name: db-secret
    mountPath: /app/secrets/db
    readOnly: true
volumes:
  - name: db-secret
    secret:
      secretName: db-secret

# 方式三：使用 External Secrets Operator（推荐生产环境）
# 从 Vault/AWS SM/Azure KeyVault 同步到 K8s Secret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-secret
spec:
  refreshInterval: 1h            # 每小时从 Vault 同步一次
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: db-secret               # 创建的 K8s Secret 名称
    creationPolicy: Owner
  data:
    - secretKey: password         # K8s Secret 中的 key
      remoteRef:
        key: secret/data/order-db  # Vault 中的路径
        property: password         # Vault 中的字段
```

---

## 总结：K8s 中 Spring Cloud 微服务的全景架构

```
┌───────────────────────────────────────────────────────────────────┐
│                        Load Balancer / Ingress                     │
│                     (Nginx Ingress / Traefik)                      │
└──────────────────────────────┬────────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────────┐
│                    K8s Cluster                                     │
│                                                                    │
│  ┌── namespace: ingress ──┐                                       │
│  │  Ingress Controller    │                                       │
│  └────────────────────────┘                                       │
│                                                                    │
│  ┌── namespace: microservice ────────────────────────────────────┐│
│  │                                                               ││
│  │  Gateway (Deployment x2, HPA 2-5)                             ││
│  │    ├── Startup/Liveness/Readiness Probes                      ││
│  │    ├── Resource: 250m-1CPU, 512Mi-1Gi                         ││
│  │    ├── PodAntiAffinity: 跨节点                                 ││
│  │    └── TopologySpreadConstraint: 跨 Zone                      ││
│  │                                                               ││
│  │  Order Service (Deployment x3, HPA 3-20)                      ││
│  │    ├── 同上探针/资源/调度策略                                   ││
│  │    ├── ConfigMap: bootstrap.yml 挂载                           ││
│  │    ├── Secret: db-password (External Secrets Operator)         ││
│  │    ├── NetworkPolicy: 只允许 gateway 和同 ns 访问              ││
│  │    └── Sidecar: SkyWalking Agent (initContainer 注入)          ││
│  │                                                               ││
│  │  User/Inventory/Payment/Notification Service...               ││
│  │                                                               ││
│  └───────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌── namespace: middleware ──────────────────────────────────────┐│
│  │                                                               ││
│  │  Nacos (StatefulSet x3, PVC 10Gi each)                        ││
│  │  Seata Server (Deployment x2)                                 ││
│  │  Sentinel Dashboard (Deployment x1)                           ││
│  │  RocketMQ NameServer (Deployment x2) + Broker (StatefulSet x2)││
│  │                                                               ││
│  └───────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌── namespace: monitoring ──────────────────────────────────────┐│
│  │                                                               ││
│  │  Prometheus + Grafana                                         ││
│  │  SkyWalking OAP + UI                                          ││
│  │  ELK Stack (Elasticsearch + Logstash + Kibana)                ││
│  │                                                               ││
│  └───────────────────────────────────────────────────────────────┘│
│                                                                    │
│  跨层依赖：                                                        │
│  微服务 → Nacos (服务发现 + 配置)                                  │
│  微服务 → Sentinel Dashboard (限流规则同步)                         │
│  微服务 → Seata (分布式事务)                                       │
│  微服务 → RocketMQ (异步消息)                                      │
│  微服务 → Prometheus (指标暴露)                                    │
│  微服务 → SkyWalking (链路追踪)                                    │
│                                                                    │
│  底层支撑：                                                        │
│  CNI: Calico/Flannel/Cilium (网络)                                │
│  CSI: cloud-provider (存储)                                       │
│  kube-proxy: IPVS 模式 (Service 负载均衡)                         │
│  CoreDNS: 服务 DNS 解析                                           │
│  Metrics Server: HPA 指标来源                                     │
└───────────────────────────────────────────────────────────────────┘
```

每一个层次、每一个组件，从内核 cgroup 对 JVM 的约束，到 CNI 插件对网络的封装，到 iptables/IPVS 对流量的路由，到探针对健康状态的判定，再到优雅停机的信号链——这些都是在 K8s 上运行 Spring Cloud 微服务必须理解的底层细节。只有掌握了这些，才能在生产环境中从容应对各类故障和性能问题。
