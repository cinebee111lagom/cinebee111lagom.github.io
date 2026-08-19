---
title: Kubernetes 网络层深度解析
date: 2026-09-08 08:45:00
tags:
  - Kubernetes
  - CNI
  - Calico
  - Cilium
  - 网络
categories:
  - Kubernetes
---

## 一、CNI 插件：Calico vs Cilium

### 1. CNI 工作原理

```
┌─────────────────────────────────────────────────────────┐
│                    kubelet 调用链                         │
│                                                          │
│  Pod 创建 → CRI 调用 → CNI 二进制执行 → 配置网络 → Pod 就绪  │
│                                                          │
│  /opt/cni/bin/          /etc/cni/net.d/                  │
│  ├── calico             ├── 10-calico.conflist           │
│  ├── cilium-cni         ├── 05-cilium.conflist           │
│  ├── bridge             └── 链式调用配置                    │
│  ├── flannel                                                │
│  └── host-local                                             │
└─────────────────────────────────────────────────────────┘
```



### 2. Calico 架构详解

```yaml
# Calico 核心组件
components:
  felix:
    role: "每个节点的 Agent"
    duty: "编程 iptables/eBPF 规则、管理路由表"
    detail: |
      - 监听 etcd/API Server 中的 NetworkPolicy 变更
      - 将策略转换为 iptables 规则或 eBPF 程序
      - 管理 veth pair 和路由信息

  BIRD:
    role: "BGP 路由守护进程"
    duty: "在节点间交换路由信息"
    detail: |
      - 每个节点运行 BIRD 实例
      - 通过 BGP 协议宣告 Pod CIDR 路由
      - 支持 Route Reflector 减少全互联开销

  Typha:
    role: "API Server 代理/缓存层"
    duty: "减少 API Server 压力"
    detail: |
      - 位于 Felix 和 API Server 之间
      - 合并多个 Felix 的 Watch 请求
      - 在大规模集群中至关重要（>100 节点）
```



**Calico 数据平面模式对比：**

```
┌──────────────────────────────────────────────────────────────┐
│                    iptables 模式（传统）                       │
│                                                               │
│  Pod A ──veth──┐                        ┌──veth── Pod C       │
│                ├── caliXXX ── 路由 ── caliXXX ──┤              │
│  Pod B ──veth──┘        ↓                └──veth── Pod D       │
│                    iptables                                     │
│                    FORWARD Chain                                │
│                    cali-FORWARD                                 │
│                    cali-INPUT / cali-OUTPUT                    │
│                    ──────────────────                           │
│                    10000+ 规则时性能下降显著                      │
│                    规则线性匹配 O(n)                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    eBPF 模式（推荐）                           │
│                                                               │
│  Pod A ──veth──┐                        ┌──veth── Pod C       │
│                ├── TC/eBPF ── 直通 ── TC/eBPF ──┤              │
│  Pod B ──veth──┘     ↓                       └──veth── Pod D  │
│                 eBPF 程序                                       │
│                 在网卡驱动层/TC层执行                             │
│                 哈希表查找 O(1)                                  │
│                 绕过 iptables 完全                              │
│                 ──────────────────                              │
│                 支持 DSR (Direct Server Return)                 │
│                 Service 负载均衡也在 eBPF 中完成                  │
└──────────────────────────────────────────────────────────────┘
```

```yaml
# Calico eBPF 模式启用
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    linuxDataplane: BPF          # 启用 eBPF 数据平面
    hostPorts: Disabled           # eBPF 模式下 hostPorts 由 eBPF 处理
  calicoNodeDaemonSet:
    spec:
      template:
        spec:
          containers:
            - name: calico-node
              env:
                - name: FELIX_BPFENABLED
                  value: "true"
                - name: FELIX_BPFEXTERNALSERVICEMODE
                  value: "DSR"   # DSR 模式，回程流量不经过 LB
```

### 3. Cilium 架构详解

```yaml
# Cilium 核心组件
components:
  cilium-agent:
    role: "每个节点的守护进程"
    duty: "管理 eBPF 程序、提供 CNI 功能"
    detail: |
      - 加载 eBPF 程序到内核
      - 管理 Endpoint（Pod 网络接口）
      - 提供 L3/L4/L7 网络策略
      - 内置 Service Mesh sidecar 替代方案

  cilium-operator:
    role: "集群级控制平面"
    duty: "管理全局资源"
    detail: |
      - 分配 Pod CIDR
      - 管理 CRD 资源
      - KVStore 一致性维护

  Hubble:
    role: "可观测性平台"
    duty: "网络流量可视化与监控"
    detail: |
      - 基于 eBPF 的流量捕获
      - L3/L4/L7 流量日志
      - Prometheus 指标导出
      - Relay 组件聚合多节点数据
```

**Cilium eBPF 数据路径：**

```
┌─────────────────────────────────────────────────────────────┐
│                   Cilium eBPF 数据路径                        │
│                                                              │
│   应用层 (Pod Process)                                        │
│       │                                                      │
│       ▼                                                      │
│   Socket Layer ──→ eBPF Socket 程序 (可选 L7 可见性)          │
│       │                                                      │
│       ▼                                                      │
│   TCP/IP 协议栈                                               │
│       │                                                      │
│       ▼                                                      │
│   TC (Traffic Control) 层 ──→ eBPF TC 程序                   │
│       │                           │                          │
│       │                    ┌──────┴──────┐                   │
│       │                    │  策略引擎     │                   │
│       │                    │  - L3 过滤    │                   │
│       │                    │  - L4 过滤    │                   │
│       │                    │  - L7 过滤    │                   │
│       │                    │  (HTTP/gRPC)  │                   │
│       │                    └──────┬──────┘                   │
│       │                           │                          │
│       ▼                           ▼                          │
│   BPF_MAP 查询 ──→ 路由决策 ──→ 转发/丢弃                    │
│       │                                                      │
│       ▼                                                      │
│   网卡驱动 (XDP 可选，用于 DDoS 防护)                         │
│       │                                                      │
│       ▼                                                      │
│   物理网络                                                    │
└─────────────────────────────────────────────────────────────┘
```

### 4. AI 推理场景 CNI 选型对比

```
┌─────────────────┬──────────────────────┬──────────────────────┐
│     维度         │      Calico          │      Cilium          │
├─────────────────┼──────────────────────┼──────────────────────┤
│ 数据平面性能     │ iptables 较慢        │ eBPF 极快            │
│                 │ eBPF 模式接近 Cilium  │ 原生 eBPF            │
├─────────────────┼──────────────────────┼──────────────────────┤
│ Network Policy  │ L3/L4                │ L3/L4/L7             │
│                 │ 标准 K8s NP + CRD    │ 支持 HTTP/gRPC 路由级 │
├─────────────────┼──────────────────────┼──────────────────────┤
│ Service Mesh    │ 需配合 Istio         │ 内置 Sidecar-free    │
│                 │ 有 eBPF 加速方案      │ 替代 envoy sidecar   │
├─────────────────┼──────────────────────┼──────────────────────┤
│ 可观测性         │ 需额外工具            │ Hubble 原生集成       │
│                 │ 流日志有限            │ L7 级流量可视化       │
├─────────────────┼──────────────────────┼──────────────────────┤
│ GPU 直通兼容     │ 良好                 │ 良好                 │
│ RDMA/SR-IOV     │ 需手动配置            │ 有专门支持            │
├─────────────────┼──────────────────────┼──────────────────────┤
│ 运维复杂度       │ 低，成熟稳定          │ 中高，概念较多        │
├─────────────────┼──────────────────────┼──────────────────────┤
│ 大规模集群       │ Typha 缓解压力        │ 原生支持大规模        │
│ (>500 节点)     │ 需调优                │ etcd/CRD 双模式      │
├─────────────────┼──────────────────────┼──────────────────────┤
│ AI 推理推荐场景  │ 传统混合部署、         │ 高性能推理、         │
│                 │ 多租户安全优先         │ L7 策略、Mesh 需求   │
└─────────────────┴──────────────────────┴──────────────────────┘
```

---

## 二、Service Mesh：推理服务流量治理

### 1. Istio 架构与推理场景

```
┌──────────────────────────────────────────────────────────────┐
│                    Istio 架构（Ambient Mesh 模式）             │
│                                                               │
│   控制平面                                                     │
│   ┌─────────────────────────────────────────────┐            │
│   │  istiod                                      │            │
│   │  ├── Pilot: 配置分发 (xDS API)               │            │
│   │  ├── Citadel: 证书管理 (mTLS)                │            │
│   │  └── Galley: 配置验证与处理                   │            │
│   └─────────────────────────────────────────────┘            │
│                                                               │
│   数据平面 - Sidecar 模式（传统）                              │
│   ┌──────────────────────────┐                               │
│   │  推理 Pod                 │                               │
│   │  ┌──────┐  ┌──────────┐  │                               │
│   │  │vLLM  │←→│ Envoy    │  │  ← Sidecar, 每 Pod 一个       │
│   │  │容器   │  │ Proxy    │  │    资源开销 ~100MB 内存        │
│   │  └──────┘  └──────────┘  │                               │
│   └──────────────────────────┘                               │
│                                                               │
│   数据平面 - Ambient 模式（推荐）                              │
│   ┌──────────────────────────┐                               │
│   │  推理 Pod                 │                               │
│   │  ┌──────┐                │  ← 无 Sidecar                 │
│   │  │vLLM  │  ztunnel 代理   │  ← L4 层节点级代理             │
│   │  │容器   │  (每节点一个)   │  ← mTLS 透明加密              │
│   │  └──────┘                │                               │
│   │         waypoint proxy   │  ← L7 层按需部署               │
│   │         (按命名空间部署)  │  ← 仅需要 L7 策略时创建        │
│   └──────────────────────────┘                               │
└──────────────────────────────────────────────────────────────┘
```

### 2. 推理服务流量管理实战

```yaml
# VirtualService: 推理服务灰度发布（A/B 测试）
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: llm-inference-routing
  namespace: inference
spec:
  hosts:
    - llm-service
  http:
    # 基于请求头路由：内部测试流量到新模型
    - match:
        - headers:
            x-model-version:
              exact: "v2-experimental"
      route:
        - destination:
            host: llm-service
            subset: v2
            port:
              number: 8000
      timeout: 60s                    # 推理超时较长

    # 金丝雀发布：10% 流量到新版本
    - route:
        - destination:
            host: llm-service
            subset: v1
          weight: 90
        - destination:
            host: llm-service
            subset: v2
          weight: 10
      retries:
        attempts: 2
        retryOn: "503,reset,connect-failure"
        perTryTimeout: 30s
      timeout: 120s                   # LLM 推理可能需要较长时间

---
# DestinationRule: 推理服务子集定义
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: llm-inference-dr
  namespace: inference
spec:
  host: llm-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
        connectTimeout: 5s
      http:
        h2UpgradePolicy: DEFAULT       # gRPC 推理默认升级 HTTP/2
        maxRequestsPerConnection: 100   # 推理请求保持连接
        maxConcurrentStreams: 50        # HTTP/2 多路复用
    outlierDetection:
      consecutive5xxErrors: 3          # 3次5xx后摘除
      interval: 30s
      baseEjectionTime: 60s
      maxEjectionPercent: 30           # 最多摘除30%实例
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
      trafficPolicy:
        connectionPool:
          http:
            maxConcurrentStreams: 20     # v2 新版本限制并发
```

```yaml
# 限流与熔断：保护推理服务
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: inference-rate-limit
  namespace: inference
spec:
  workloadSelector:
    labels:
      app: llm-service
  configPatches:
    - applyTo: HTTP_FILTER
      match:
        context: SIDECAR_INBOUND
        listener:
          filterChain:
            filter:
              name: envoy.filters.network.http_connection_manager
              subFilter:
                name: envoy.filters.http.router
      patch:
        operation: INSERT_BEFORE
        value:
          name: envoy.filters.http.local_ratelimit
          typed_config:
            "@type": type.googleapis.com/udpa.type.v1.TypedStruct
            type_url: >-
              type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
            value:
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 100          # 每个实例每秒最多 100 请求
                tokens_per_fill: 100
                fill_interval: 1s
              filter_enabled:
                runtime_key: local_rate_limit_enabled
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              filter_enforced:
                runtime_key: local_rate_limit_enforced
                default_value:
                  numerator: 100
                  denominator: HUNDRED
```

### 3. Cilium Service Mesh（Sidecar-free）

```yaml
# Cilium Ingress with L7 路由
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: llm-inference-ingress
  namespace: inference
  annotations:
    kubernetes.io/ingress.class: cilium
spec:
  rules:
    - host: inference.internal
      http:
        paths:
          - path: /v1/completions
            pathType: Prefix
            backend:
              service:
                name: llm-completions
                port:
                  number: 8000
          - path: /v1/embeddings
            pathType: Prefix
            backend:
              service:
                name: llm-embeddings
                port:
                  number: 8001

---
# CiliumEnvoyConfig: 高级 L7 策略
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: inference-rate-limit
  namespace: inference
spec:
  services:
    - name: llm-service
      namespace: inference
  resources:
    - "@type": type.googleapis.com/envoy.config.listener.v3.Listener
      name: envoy-l7-listener
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": >-
                  type.googleapis.com/envoy.extensions.filters.network
                  .http_connection_manager.v3.HttpConnectionManager
                stat_prefix: inference
                http_filters:
                  - name: envoy.filters.http.router
                route_config:
                  virtual_hosts:
                    - name: inference
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/v1/chat/completions"
                          route:
                            cluster: llm-service
                            timeout: 120s
                            retry_policy:
                              retry_on: "503"
                              num_retries: 2
```

---

## 三、Network Policy：多租户安全隔离

### 1. 标准 NetworkPolicy 深度解析

```yaml
# 推理服务完整 NetworkPolicy 套件
---
# 策略1: 默认拒绝所有入站流量
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: inference-team-a
spec:
  podSelector: {}           # 匹配命名空间内所有 Pod
  policyTypes:
    - Ingress

---
# 策略2: 仅允许 API Gateway 访问推理服务
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-gateway-to-inference
  namespace: inference-team-a
spec:
  podSelector:
    matchLabels:
      app: llm-inference
  policyTypes:
    - Ingress
  ingress:
    - from:
        # 仅允许 gateway 命名空间中的 gateway Pod
        - namespaceSelector:
            matchLabels:
              name: api-gateway
          podSelector:
            matchLabels:
              app: gateway
      ports:
        - protocol: TCP
          port: 8000          # vLLM 推理端口
        - protocol: TCP
          port: 8080          # Prometheus metrics 端口（可选）

---
# 策略3: 允许推理服务访问模型存储（S3/MinIO）
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-inference-to-model-store
  namespace: inference-team-a
spec:
  podSelector:
    matchLabels:
      app: llm-inference
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: model-storage
          podSelector:
            matchLabels:
              app: minio
      ports:
        - protocol: TCP
          port: 9000          # MinIO S3 端口
    # 允许 DNS 解析
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53

---
# 策略4: 允许推理服务之间的 Pod 通信（分布式推理）
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-intra-team-inference
  namespace: inference-team-a
spec:
  podSelector:
    matchLabels:
      app: llm-inference
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: llm-inference     # 同标签 Pod 互通
      ports:
        - protocol: TCP
          port: 29500               # PyTorch 分布式通信端口
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: llm-inference
      ports:
        - protocol: TCP
          port: 29500
        - protocol: TCP
          port: 8000
```

### 2. Cilium NetworkPolicy（L7 级别）

```yaml
# Cilium: L7 HTTP 级策略 - 仅允许特定 API 路径
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: inference-api-allowlist
  namespace: inference-team-a
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
          rules:
            http:
              - method: "POST"
                path: "/v1/chat/completions"
              - method: "POST"
                path: "/v1/embeddings"
              - method: "GET"
                path: "/v1/models"
              - method: "GET"
                path: "/health"
                # 显式拒绝其他路径

---
# Cilium: 限制出站只能访问特定外部服务
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: restrict-external-access
  namespace: inference-team-a
spec:
  endpointSelector:
    matchLabels:
      app: llm-inference
  egress:
    # 允许访问模型仓库
    - toFQDNs:
        - matchName: "models.internal.company.com"
        - matchPattern: "*.s3.amazonaws.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
          rules:
            tls:
              - {}    # 允许 TLS
    # 允许访问 Tokenizer 服务
    - toEndpoints:
        - matchLabels:
            app: tokenizer
      toPorts:
        - ports:
            - port: "8002"
              protocol: TCP
    # DNS
    - toEndpoints:
        - matchLabels:
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
          rules:
            dns:
              - matchPattern: "*.internal.company.com"
              - matchPattern: "*.s3.amazonaws.com"
```

### 3. 多租户隔离完整架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    多租户推理平台隔离架构                          │
│                                                                  │
│  ┌──── 租户 A ──────────────┐  ┌──── 租户 B ──────────────┐     │
│  │ namespace: inference-a   │  │ namespace: inference-b   │     │
│  │                          │  │                          │     │
│  │ ┌──────────────────────┐ │  │ ┌──────────────────────┐ │     │
│  │ │ llm-inference Pod    │ │  │ │ llm-inference Pod    │ │     │
│  │ │ - L3: 仅同 NS 互通   │ │  │ │ - L3: 仅同 NS 互通   │ │     │
│  │ │ - L4: 仅端口 8000    │ │  │ │ - L4: 仅端口 8000    │ │     │
│  │ │ - L7: POST /v1/...  │ │  │ │ - L7: POST /v1/...  │ │     │
│  │ └──────────────────────┘ │  │ └──────────────────────┘ │     │
│  │         ↕                │  │         ↕                │     │
│  │ ┌──────────────────────┐ │  │ ┌──────────────────────┐ │     │
│  │ │ model-store PVC      │ │  │ │ model-store PVC      │ │     │
│  │ │ (加密，仅本 NS 可挂)  │ │  │ │ (加密，仅本 NS 可挂)  │ │     │
│  │ └──────────────────────┘ │  │ └──────────────────────┘ │     │
│  └──────────────────────────┘  └──────────────────────────┘     │
│              ↑                              ↑                    │
│              └──────────┬───────────────────┘                    │
│                         │                                        │
│  ┌──────────────────────┴──────────────────────────────────┐    │
│  │  api-gateway 命名空间                                     │    │
│  │  ┌──────────────────────────────────────────────────┐   │    │
│  │  │ Gateway Pod (Envoy/NGINX/Cilium Gateway)         │   │    │
│  │  │  - 路由到对应租户 NS                                │   │    │
│  │  │  - 鉴权 (JWT/OAuth)                               │   │    │
│  │  │  - 全局限流                                        │   │    │
│  │  │  - 租户间流量完全隔离                               │   │    │
│  │  └──────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、AI 推理场景的特殊网络考量

### 1. 大模型推理的网络挑战

```
┌─────────────────────────────────────────────────────────────┐
│            LLM 推理网络特征 vs 传统 Web 服务                  │
│                                                              │
│  传统 Web 推理          LLM 推理                              │
│  ───────────           ─────────                             │
│  响应: <100ms           响应: 2s-120s                          │
│  Body: <10KB            Body: 1KB-2MB (长文本)                │
│  并发: 10000+ QPS       并发: 10-500 QPS (GPU 受限)           │
│  连接: 短连接为主        连接: 长连接/SSE 流式                  │
│  超时: 5s               超时: 120s+                            │
│                                                              │
│  推理特殊需求:                                                │
│  ✗ 普通负载均衡器超时配置不够                                  │
│  ✗ Envoy 默认 stream timeout 可能中断长推理                    │
│  ✗ SSE 流式响应需要特别的缓冲策略                              │
│  ✗ 模型加载需要拉取 GB-TB 级权重文件                           │
│  ✗ 多机推理需要 RDMA/高速网络（Tensor Parallel）               │
└─────────────────────────────────────────────────────────────┘
```

### 2. Envoy 超时配置优化（针对 LLM）

```yaml
# EnvoyFilter: 推理服务专用超时配置
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: llm-timeout-config
  namespace: inference
spec:
  workloadSelector:
    labels:
      app: llm-inference
  configPatches:
    # 入站连接超时
    - applyTo: NETWORK_FILTER
      match:
        listener:
          filterChain:
            filter:
              name: envoy.filters.network.http_connection_manager
      patch:
        operation: MERGE
        value:
          stream_idle_timeout: 300s       # 5分钟空闲超时
          request_timeout: 180s           # 请求总超时
          common_http_protocol_options:
            idle_timeout: 600s            # 连接空闲超时

    # 上游集群超时
    - applyTo: CLUSTER
      match:
        cluster:
          service: llm-service
      patch:
        operation: MERGE
        value:
          typed_extension_protocol_options:
            envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
              "@type": >-
                type.googleapis.com/envoy.extensions.upstreams.http.v3
                .HttpProtocolOptions
              explicit_http_config:
                http2_protocol_options:
                  initial_stream_window_size: 1048576    # 1MB 流窗口
                  initial_connection_window_size: 2097152 # 2MB 连接窗口
```

### 3. 高速互联（RDMA/InfiniBand）场景

```yaml
# 为多机推理配置 SR-IOV + RDMA
# 1. 安装 SR-IOV Network Operator
# 2. 配置 SriovNetworkNodePolicy
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetworkNodePolicy
metadata:
  name: rdma-policy
  namespace: sriov-network-operator
spec:
  resourceName: rdma_nic
  nodeSelector:
    feature.node.kubernetes.io/custom-rdma: "true"
  priority: 99
  mtu: 9000                          # Jumbo Frame
  numVfs: 8                          # 每个物理网卡创建 8 个 VF
  nicSelector:
    pfNames:
      - ens3f0                        # 物理网卡名称
  deviceType: netdevice               # 使用 netdevice 驱动（非 vfio）
  isRdma: true                        # 启用 RDMA

---
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: rdma-net
  namespace: inference
spec:
  config: |
    {
      "cniVersion": "0.3.1",
      "type": "sriov",
      "name": "rdma-net",
      "vlan": 100,
      "ipam": {
        "type": "whereabouts",
        "range": "192.168.100.0/24"
      }
    }

---
# Pod 中挂载 RDMA 网络
apiVersion: v1
kind: Pod
metadata:
  name: llm-tp-worker
  namespace: inference
  annotations:
    k8s.v1.cni.cncf.io/networks: rdma-net
spec:
  containers:
    - name: vllm-worker
      image: vllm/vllm-openai:latest
      resources:
        limits:
          nvidia.com/gpu: 4
          intel.com/rdma_nic: 1       # SR-IOV VF 资源
      env:
        - name: NCCL_IB_DISABLE
          value: "0"                   # 启用 InfiniBand
        - name: NCCL_IB_HCA
          value: "mlx5"               # Mellanox 网卡
        - name: NCCL_SOCKET_IFNAME
          value: "net1"               # 使用 SR-IOV 网络接口
```

### 4. 网络性能调优清单

```
┌────────────────────────────────────────────────────────────────┐
│           AI 推理集群网络调优 Checklist                          │
│                                                                 │
│  基础网络层:                                                     │
│  □ MTU 调整为 9000 (Jumbo Frame)，减少小包开销                    │
│  □ TCP 内核参数调优:                                              │
│    - net.core.rmem_max = 134217728                              │
│    - net.core.wmem_max = 134217728                              │
│    - net.ipv4.tcp_rmem = 4096 87380 134217728                   │
│    - net.ipv4.tcp_wmem = 4096 65536 134217728                   │
│    - net.core.netdev_max_backlog = 30000                        │
│  □ 开启 TCP BBR 拥塞控制算法                                     │
│                                                                 │
│  CNI 层:                                                        │
│  □ 选择 eBPF 数据平面（Cilium 或 Calico eBPF）                   │
│  □ 关闭不需要的加密（如果在可信网络内）                            │
│  □ 确认 Pod-to-Pod 带宽 > 模型加载需求                           │
│                                                                 │
│  Service Mesh 层:                                                │
│  □ 推理服务超时设置为 120s+                                       │
│  □ SSE 流式响应设置适当的 buffer                                  │
│  □ Envoy stream_idle_timeout 调高                               │
│  □ HTTP/2 多路复用窗口调大                                        │
│  □ Sidecar 资源 limits 设置合理（尤其内存）                       │
│                                                                 │
│  安全层:                                                         │
│  □ 默认拒绝所有流量，按需开放                                     │
│  □ L7 策略限制 API 路径（防止模型被滥用）                         │
│  □ Egress 限制（防止权重泄露）                                   │
│  □ mTLS 加密推理请求/响应（敏感数据场景）                         │
│                                                                 │
│  高速互联（多机推理）:                                            │
│  □ RDMA/SR-IOV 部署与验证                                        │
│  □ NCCL 环境变量配置正确                                         │
│  □ 网卡亲和性 (CPU-NIC Affinity) 绑定                           │
│  □ InfiniBand 子网管理器 (SM) 高可用                             │
└────────────────────────────────────────────────────────────────┘
```

这三层网络架构在 AI 推理场景中各有侧重：**CNI 决定底座性能**，**Service Mesh 管流量治理**，**Network Policy 守安全边界**。实际部署时需要根据推理服务的规模、多租户需求和性能要求做针对性选型和调优。有哪个层面想继续深入吗？
