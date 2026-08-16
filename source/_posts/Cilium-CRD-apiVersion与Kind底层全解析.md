---
title: Cilium CRD 的 apiVersion / Kind 底层全解析
date: 2026-09-07 13:00:00
tags:
  - Cilium
  - CRD
  - Kubernetes
  - eBPF
categories:
  - Kubernetes
---

作为一名长期运维 Cilium 的 K8s 管理员，我把 Cilium 所有核心 CRD 的 `apiVersion`、`kind` 以及它们背后对应的**内核态行为**逐层拆解。

---

## 一、Cilium CRD 全景图

```bash
# 列出集群中所有 Cilium 相关的 CRD
kubectl get crd | grep cilium
```

输出示例：

```
ciliumclusterwidenetworkpolicies.cilium.io    2024-01-15
ciliumendpoints.cilium.io                     2024-01-15
ciliumenvoyconfigs.cilium.io                  2024-01-15
ciliumexternalworkloads.cilium.io             2024-01-15
ciliumidentities.cilium.io                    2024-01-15
ciliumlocalredirectpolicies.cilium.io         2024-01-15
ciliumnetworkpolicies.cilium.io               2024-01-15
ciliumnodeconfigs.cilium.io                   2024-01-15
ciliumnodes.cilium.io                         2024-01-15
ciliumpodippools.cilium.io                    2024-01-15
```

所有 Cilium CRD 统一使用 **apiGroup: `cilium.io`**，版本随 Cilium 发布周期演进。

---

## 二、核心 CRD 逐个拆解

### 2.1 CiliumNetworkPolicy（CNP）

```yaml
apiVersion: cilium.io/v2          # ← apiVersion
kind: CiliumNetworkPolicy         # ← kind
metadata:
  name: allow-frontend
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          rules:
            http:
              - method: GET
                path: "/api/.*"
  # 这些在原生 K8s NetworkPolicy 中完全不存在
```

**与原生 K8s NetworkPolicy 的对比：**

| 维度 | K8s NetworkPolicy | CiliumNetworkPolicy |
|---|---|---|
| apiVersion | `networking.k8s.io/v1` | `cilium.io/v2` |
| kind | `NetworkPolicy` | `CiliumNetworkPolicy` |
| L3 过滤 | podSelector / namespaceSelector | endpointSelector / fromEndpoints |
| L4 过滤 | port + protocol | toPorts |
| **L7 过滤** | **不支持** | **HTTP/gRPC/Kafka/DNS 级别过滤** |
| DNS 策略 | 不支持 | `toFQDNs`（基于域名而非 IP） |
| 作用范围 | 仅当前 namespace | 可用 `matchPattern: *` 跨 namespace |

**底层实现：**

```
CiliumNetworkPolicy YAML
        │
        ▼
Cilium Agent (cilium-agent Pod) Watch API Server
        │
        ▼ 解析 L3/L4/L7 规则
        │
        ├──L3/L4──▶ eBPF 程序编译 & 加载到 Pod 的 TC (Traffic Control) hook
        │           ├── ingress: tc ingress → BPF prog
        │           └── egress:  tc egress  → BPF prog
        │
        └──L7 (HTTP/gRPC)──▶ 嵌入式 Envoy 实例
                              ├── 每个节点运行一个 Envoy
                              ├── 通过 xDS (LDS/RDS/CDS/EDS) 接收规则
                              └── 对匹配流量做 L7 协议解析和过滤
```

```bash
# 查看某 Pod 上加载的 eBPF 程序
kubectl exec -n kube-system <cilium-pod> -- cilium bpf endpoint list

# 查看 eBPF policy map（实际生效的规则）
kubectl exec -n kube-system <cilium-pod> -- \
  cilium bpf policy get <endpoint-id>
```

### 2.2 CiliumClusterwideNetworkPolicy（CCNP）

```yaml
apiVersion: cilium.io/v2                    # ← 同一个 apiGroup
kind: CiliumClusterwideNetworkPolicy        # ← 集群级别 kind
metadata:
  name: deny-all-ingress-clusterwide
spec:
  endpointSelector: {}                      # 匹配所有 Pod
  ingress:
    - fromEndpoints:
        - matchLabels:
            "k8s:io.kubernetes.pod.namespace": kube-system
```

**底层差异：**

- `CiliumNetworkPolicy` 是 **Namespaced** 资源，规则只作用于同 namespace 内的 endpoint
- `CiliumClusterwideNetworkPolicy` 是 **Cluster-scoped** 资源，规则作用于整个集群
- 两者底层都编译为相同的 eBPF policy map，区别仅在 **cilium-agent 的 watch 范围和 selector 逻辑**

```bash
# 查看集群范围的策略
kubectl get ccnp

# 查看命名空间范围的策略
kubectl get cnp -A
```

### 2.3 CiliumEndpoint（CEP）

```yaml
apiVersion: cilium.io/v2
kind: CiliumEndpoint
metadata:
  name: my-app-6f8b9c4d5-x7k2z
  namespace: production
status:
  identity:
    id: 12345                        # ← Cilium Identity ID
    labels:
      - app=my-app
      - env=production
  networking:
    addressing:
      - ipv4: 10.244.1.15
        ipv6: "fd00::a"
    node: 192.168.1.10
  encryption:
    mode: disabled
  policy:
    ingress:
      enforcing: true
      allowed:
        - 12344                       # 允许的 source identity ID
    egress:
      enforcing: true
```

**底层细节：**

这是 Cilium 的核心数据结构之一。每个 Pod 启动时：

```
Pod 创建 (Kubelet)
    │
    ▼
CNI 插件 (cilium-cni) 被调用
    │ 分配 IP、创建 veth pair
    │
    ▼
Cilium Agent 为该 Pod 创建 CiliumEndpoint 对象
    │
    ├── 分配 Security Identity（基于 labels）
    │   相同 label 组合的 Pod 共享同一个 Identity
    │
    ├── 写入 BPF Endpoint Map
    │   └── 每个 endpoint → 对应的 BPF 程序集合
    │       ├── tc ingress prog
    │       ├── tc egress prog
    │       ├── socket-level prog (sock_ops)
    │       └── cgroup-level prog (connect4/sendmsg)
    │
    └── 写入 BPF Policy Map
        └── Identity → Allow/Deny 的映射表
            key: (remote_identity, dst_port, protocol)
            val: proxy_port (L7 redirect) or allow/deny
```

```bash
# 查看 CiliumEndpoint 列表
kubectl get cep -A

# 查看具体 endpoint 的 eBPF 程序
kubectl exec -n kube-system <cilium-pod> -- \
  cilium endpoint list

# 查看 endpoint 的 policy verdict
kubectl exec -n kube-system <cilium-pod> -- \
  cilium endpoint get <endpoint-id> -o json | jq '.policy'
```

### 2.4 CiliumIdentity（CID）

```yaml
apiVersion: cilium.io/v2
kind: CiliumIdentity
metadata:
  name: "12345"
  labels:
    app: my-app
    env: production
    "k8s:io.kubernetes.pod.namespace": production
security-labels:
  app: my-app
  env: production
  "k8s:io.kubernetes.pod.namespace": production
```

**这是 Cilium 安全模型的灵魂：**

```
传统 K8s NetworkPolicy:
  Pod IP → 规则判断（IP 可变，Pod 重启后 IP 变化）

Cilium:
  Pod → Identity (基于 labels，不变) → BPF Policy Map 查询
         │
         │  Identity 是稳定的：
         │  - Pod 重建、IP 变化 → Identity 不变
         │  - 只有 labels 变化时 Identity 才会变
         │
         ▼
  BPF map: {src_identity, dst_identity, port, proto} → allow/deny
```

这意味着 Cilium 的策略是 **identity-based** 而非 **IP-based**，在大规模集群中效率远超 iptables。

```bash
# 查看所有 Identity
kubectl get ciliumidentities

# 查看 Identity 与 endpoint 的映射
kubectl exec -n kube-system <cilium-pod> -- \
  cilium identity list
```

### 2.5 CiliumNode（CN）

```yaml
apiVersion: cilium.io/v2
kind: CiliumNode
metadata:
  name: worker-01
spec:
  addresses:
    - ip: 192.168.1.10
      type: InternalIP
  encryption:
    key: 5
  health:
    ipv4: 10.244.0.243
  ipam:
    default: "10.244.1.0/24"
    podCIDRs:
      - 10.244.1.0/24
    pool:
      "10.244.1.1":
        owner: default/my-app-xxx
      "10.244.1.2":
        owner: default/my-app-yyy
```

**底层细节：**

- Cilium Agent 在每个节点上创建 `CiliumNode` 对象
- **IPAM（IP 地址管理）** 状态存储在这里：哪个 IP 分配给了哪个 Pod
- 当使用 **ENI 模式（AWS）** 或 **Azure IPAM** 时，这里还会记录云厂商 ENI/NIC 绑定信息
- **Cluster Mesh** 场景下，跨集群的 CiliumNode 信息被同步，实现跨集群 Pod 直接通信

```bash
# 查看所有 CiliumNode
kubectl get ciliumnodes -o wide

# 查看某节点的 IPAM 分配
kubectl get ciliumnode worker-01 -o jsonpath='{.spec.ipam.pool}' | jq
```

### 2.6 CiliumEnvoyConfig（CEC）

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: my-envoy-config
  namespace: production
spec:
  resources:
    listeners:
      - name: my-listener
        address:
          socketAddress:
            address: "0.0.0.0"
            portValue: 10000
        filterChains:
          - filters:
              - name: envoy.filters.network.http_connection_manager
                typedConfig:
                  "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                  stat_prefix: my-listener
                  routeConfig:
                    virtualHosts:
                      - domains: ["*"]
                        routes:
                          - match:
                              prefix: "/"
                            route:
                              cluster: my-upstream
                  httpFilters:
                    - name: envoy.filters.http.router
    clusters:
      - name: my-upstream
        type: EDS
        edsClusterConfig:
          serviceName: production/my-service
```

**底层机制：**

```
CiliumEnvoyConfig YAML
        │
        ▼
Cilium Agent Watch
        │
        ▼ 通过 Unix Domain Socket 与嵌入式 Envoy 通信
        │
        ├── xDS push (LDS/RDS/CDS/EDS)
        │   └── Envoy 动态更新 listener/cluster/route 配置
        │
        └── BPF 层面：
            ├── 对匹配的流量，BPF 程序将数据包重定向到 Envoy
            │   via: bpf_redirect_peer() 或 proxy_port mapping
            └── Envoy 处理完后，回注到原始路径
```

这是 **Gateway API / Ingress / 可观测性** 的底层基础。

```bash
# 查看所有 CiliumEnvoyConfig
kubectl get ciliumenvoyconfigs -A

# 查看 Envoy 配置状态
kubectl exec -n kube-system <cilium-pod> -- \
  cilium envoy admin config-dump
```

### 2.7 CiliumLocalRedirectPolicy（CLRP）

```yaml
apiVersion: cilium.io/v2
kind: CiliumLocalRedirectPolicy
metadata:
  name: node-local-dns
  namespace: kube-system
spec:
  redirectFrontend:
    addressMatcher:
      ip: "169.254.20.10"
      port: 53
      protocol: UDP
  redirectBackend:
    localEndpointSelector:
      matchLabels:
        k8s-app: node-local-dns
    toPorts:
      - port: "53"
        protocol: UDP
```

**底层细节：**

```
正常流量路径:
  Pod → CoreDNS ClusterIP (10.96.0.10:53) → kube-proxy DNAT → CoreDNS Pod

启用 NodeLocal DNSCache 后:
  Pod → 169.254.20.10:53
        │
        ▼ Cilium BPF 层拦截
        │  (不经过 kube-proxy，不在 netfilter 路径上)
        │
        ▼ BPF 直接重定向到本节点 NodeLocal DNS Pod
            → 命中缓存 → 直接返回
            → 未命中 → 转发给 CoreDNS ClusterIP
```

Cilium 用 **eBPF socket-level hook（`bpf_sk_lookup` / `connect4`）** 实现，比 iptables redirect 延迟低一个数量级。

---

## 三、apiVersion 演进路线

```
cilium.io/v2alpha1  →  早期实验性 CRD（已废弃）
cilium.io/v2        →  当前稳定版本（Cilium 1.12+）

Gateway API 相关（非 cilium.io 域）:
  gateway.networking.k8s.io/v1      → Cilium 作为 Gateway API 实现
  gateway.networking.k8s.io/v1alpha2 → GAMMA (Gateway API for Mesh)
```

**查看已安装 CRD 的具体版本：**

```bash
kubectl get crd ciliumnetworkpolicies.cilium.io -o jsonpath='{.spec.versions[*].name}'
# 输出: v2 v2alpha1

# 查看 CRD schema（验证支持哪些字段）
kubectl get crd ciliumnetworkpolicies.cilium.io \
  -o jsonpath='{.spec.versions[?(@.name=="v2")].schema.openAPIV3Schema}' | jq '.properties.spec'
```

---

## 四、底层 BPF Map 与 CRD 的对应关系

| CRD | 对应的 BPF Map | Map 类型 | 作用 |
|---|---|---|---|
| `CiliumIdentity` | `cilium_policy_*` (policy map) | Hash | identity → allowed identities |
| `CiliumEndpoint` | `cilium_lxc_*` (endpoint map) | Hash | endpoint metadata |
| `CiliumNode` | `cilium_tunnel_map` | Hash | node IP → tunnel endpoint |
| `CiliumNetworkPolicy` | 编译进 BPF 程序本身 | — | 直接作为 BPF 指令执行 |
| `CiliumLocalRedirectPolicy` | `cilium_lb4_services_*` | LRU Hash | VIP → local backend 映射 |
| `CiliumEnvoyConfig` | Envoy 自身数据结构 | — | 通过 xDS 协议传递给 Envoy |

```bash
# 列出节点上所有 BPF map
kubectl exec -n kube-system <cilium-pod> -- cilium bpf map list

# 查看 policy map 内容
kubectl exec -n kube-system <cilium-pod> -- \
  cilium bpf policy get <endpoint-id> --verbose

# 查看 tunnel map（overlay 模式）
kubectl exec -n kube-system <cilium-pod> -- \
  cilium bpf tunnel list
```

---

## 五、Gateway API 与 Cilium 的集成

从 Cilium 1.13+ 开始，原生支持 Kubernetes Gateway API：

```yaml
apiVersion: gateway.networking.k8s.io/v1    # ← K8s 原生 apiVersion
kind: Gateway
metadata:
  name: my-gateway
  namespace: production
  annotations:
    gateway.networking.k8s.io/gateway-class-name: cilium    # ← 指定 Cilium 实现
spec:
  gatewayClassName: cilium
  listeners:
    - name: http
      protocol: HTTP
      port: 80
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-route
spec:
  parentRefs:
    - name: my-gateway
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: my-backend
          port: 8080
```

**Cilium 的 Gateway API 底层实现：**

```
Gateway + HTTPRoute 资源
        │
        ▼
Cilium Operator Watch
        │ 生成 CiliumEnvoyConfig (自动创建，无需手动写)
        │
        ▼
Cilium Agent 推送 xDS 配置给 Envoy
        │
        ▼
Envoy 监听 80/443 端口
        │ BPF 将入站流量重定向到 Envoy
        ▼
HTTP 路由匹配 → 转发到后端 Service
```

```bash
# 查看 Gateway 状态
kubectl get gateway my-gateway -n production

# 查看自动生成的 CiliumEnvoyConfig
kubectl get ciliumenvoyconfigs -n production

# 查看 Gateway Class
kubectl get gatewayclass cilium
```

---

## 六、日常排障速查表

```bash
# === 快速定位 CRD 状态 ===

# 检查所有 Cilium CRD 是否就绪
kubectl get crd -l app.kubernetes.io/part-of=cilium

# 检查 CiliumAgent 是否正常
kubectl get pods -n kube-system -l k8s-app=cilium

# === 策略调试 ===

# 模拟流量是否被允许
kubectl exec -n kube-system <cilium-pod> -- \
  cilium policy trace --src <src-identity> --dst <dst-identity> --dport 8080

# 查看 policy verdict 日志（实时）
kubectl exec -n kube-system <cilium-pod> -- \
  cilium monitor --type drop
kubectl exec -n kube-system <cilium-pod> -- \
  cilium monitor --type policy-verdict

# === Endpoint 调试 ===

# 查看 endpoint 状态
kubectl exec -n kube-system <cilium-pod> -- \
  cilium endpoint list

# 查看具体 endpoint 的 BPF 程序状态
kubectl exec -n kube-system <cilium-pod> -- \
  cilium endpoint health <endpoint-id>

# === Identity 调试 ===

# 查看 identity 分配
kubectl get ciliumidentity -o wide

# 检查 identity 是否有 orphaned（没有 endpoint 引用）
kubectl exec -n kube-system <cilium-pod> -- \
  cilium identity list --verbose
```

---

## 总结：CRD → Agent → BPF 的完整链路

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Server                                │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────────────────────┐  │
│  │CiliumNode│ │ CiliumId │ │  CNP   │ │CiliumEnvoyConfig    │  │
│  │(IPAM/拓扑)│ │(安全标识) │ │(L3-7策略)│ │(Envoy xDS配置)       │  │
│  └─────┬────┘ └────┬─────┘ └───┬────┘ └──────────┬──────────┘  │
│        │           │           │                  │              │
│        ▼           ▼           ▼                  ▼              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Cilium Agent (per Node)                     │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │    │
│  │  │IPAM 管理器 │ │Identity  │ │Policy    │ │Envoy 管理器│  │    │
│  │  │          │ │Cache     │ │Compiler  │ │(xDS push) │  │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │    │
│  └───────┼────────────┼────────────┼──────────────┼────────┘    │
│          ▼            ▼            ▼              ▼              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Linux Kernel (eBPF)                         │    │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────┐  │    │
│  │  │TC Hook  │ │Socket    │ │Cgroup   │ │ Envoy User  │  │    │
│  │  │(L3/L4)  │ │Hook(L4)  │ │Hook     │ │ Space Proxy │  │    │
│  │  │         │ │          │ │(connect)│ │ (L7)        │  │    │
│  │  └─────────┘ └──────────┘ └─────────┘ └─────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

每一个 CRD 字段最终都会落地上表中的某个组件。理解这条链路，就能在生产环境中做到从 YAML 到 BPF map 的端到端故障定位。

有具体场景需要深入展开的，随时提问。
