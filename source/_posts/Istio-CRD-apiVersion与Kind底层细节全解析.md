---
title: Istio CRD 的 apiVersion / Kind 底层细节全解析
date: 2026-09-07 15:30:00
tags:
  - Istio
  - CRD
  - Service Mesh
  - Kubernetes
categories:
  - Kubernetes
---

## 一、Istio CRD 全景图

```bash
# 列出所有 Istio CRD
kubectl get crd | grep istio.io

# 输出:
# authorizationpolicies.security.istio.io
# destinationrules.networking.istio.io
# envoyfilters.networking.istio.io
# gateways.networking.istio.io
# istiooperators.install.istio.io
# peerauthentications.security.istio.io
# requestauthentications.security.istio.io
# serviceentries.networking.istio.io
# sidecars.networking.istio.io
# telemetries.telemetry.istio.io
# virtualservices.networking.istio.io
# wasmplugins.extensions.istio.io
# workloadentries.networking.istio.io
# workloadgroups.networking.istio.io
```

```
Istio API Group 分类:

┌──────────────────────┬───────────────────────────────────────┐
│  API Group           │  包含的 Kind                           │
├──────────────────────┼───────────────────────────────────────┤
│  networking.istio.io │  VirtualService                       │
│                      │  DestinationRule                      │
│                      │  Gateway                              │
│                      │  ServiceEntry                         │
│                      │  Sidecar                              │
│                      │  WorkloadEntry                        │
│                      │  WorkloadGroup                        │
│                      │  EnvoyFilter                          │
│                      │  ProxyConfig                          │
├──────────────────────┼───────────────────────────────────────┤
│  security.istio.io   │  AuthorizationPolicy                  │
│                      │  PeerAuthentication                    │
│                      │  RequestAuthentication                 │
├──────────────────────┼───────────────────────────────────────┤
│  telemetry.istio.io  │  Telemetry                            │
├──────────────────────┼───────────────────────────────────────┤
│  extensions.istio.io │  WasmPlugin                           │
├──────────────────────┼───────────────────────────────────────┤
│  install.istio.io    │  IstioOperator                        │
└──────────────────────┴───────────────────────────────────────┘
```

---

## 二、networking.istio.io — 流量管理核心

### 2.1 VirtualService

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
```

```yaml
# 完整示例
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: production
spec:
  hosts:
    - reviews.production.svc.cluster.local
    - reviews                       # 短名
  gateways:
    - mesh                          # 内部网格流量
    - production/my-gateway         # 外部网关流量
  http:
    # 规则 1: 金丝雀路由
    - name: "canary-route"
      match:
        - headers:
            x-canary:
              exact: "true"
          uri:
            prefix: /api
          method:
            exact: GET
          sourceLabels:
            app: frontend
          queryParams:
            version:
              exact: "v2"
          port: 8080
      route:
        - destination:
            host: reviews
            subset: v2
            port:
              number: 9080
          weight: 100
          headers:
            request:
              set:
                x-env: canary
              remove:
                - x-internal
            response:
              add:
                x-served-by: "%DOWNSTREAM_REMOTE_ADDRESS%"
      timeout: 10s
      retries:
        attempts: 3
        perTryTimeout: 3s
        retryOn: "5xx,reset,connect-failure,retriable-4xx"
        retryRemoteLocalities: true
      fault:
        delay:
          percentage:
            value: 10.0
          fixedDelay: 5s
        abort:
          percentage:
            value: 5.0
          httpStatus: 503
      corsPolicy:
        allowOrigins:
          - exact: "https://example.com"
        allowMethods:
          - GET
          - POST
        maxAge: "24h"
      mirror:
        host: reviews
        subset: v3
      mirrorPercentage:
        value: 50.0
      retries:
        retryOn: "5xx"
        attempts: 3

    # 规则 2: 默认路由
    - route:
        - destination:
            host: reviews
            subset: v1
          weight: 90
        - destination:
            host: reviews
            subset: v2
          weight: 10

  tcp:
    - match:
        - port: 3306
      route:
        - destination:
            host: mysql
            port:
              number: 3306

  tls:
    - match:
        - port: 443
          sniHosts:
            - reviews.example.com
      route:
        - destination:
            host: reviews-external
```

**底层处理链路：**

```
VirtualService YAML
    │
    ▼ istiod Watch (K8s Informer)
    │
    ▼ Config Controller 解析
    │  ├── 验证: hosts 是否有效
    │  ├── 验证: destination host 是否存在
    │  ├── 构建 internal model (model.Config)
    │  └── 存入内存缓存
    │
    ▼ Push Context 重建
    │  ├── VirtualService 索引:
    │  │   key: (namespace, hostname)
    │  │   val: 按优先级排序的路由规则列表
    │  │
    │  └── Gateway 绑定:
    │      每个 Gateway 能看到哪些 VirtualService
    │      (通过 .spec.gateways 字段过滤)
    │
    ▼ xDS 生成 (RDS)
    │  每条 HTTP rule → Envoy Route
    │  ├── match.headers → Envoy HeaderMatcher
    │  ├── match.uri → Envoy PathMatcher (prefix/exact/regex)
    │  ├── match.method → Envoy HeaderMatcher (:method)
    │  ├── match.queryParams → Envoy QueryParameterMatcher
    │  ├── route.weightedClusters → Envoy WeightedCluster
    │  ├── fault.delay → Envoy FaultDelay
    │  ├── fault.abort → Envoy FaultAbort
    │  ├── retries → Envoy RetryPolicy
    │  ├── timeout → Envoy Timeout
    │  ├── mirror → Envoy RequestMirrorPolicy
    │  └── corsPolicy → Envoy CorsPolicy
    │
    ▼ xDS Push (gRPC ADS) → Envoy
    │
    ▼ Envoy 收到 RouteConfiguration
    │  ├── 更新 RouteMatcher
    │  ├── 每个 VirtualHost 包含多条 Route
    │  └── Route 匹配按顺序执行 (first match wins)
    │
    ▼ 请求到达时的匹配流程:
       │
       │  HTTP 请求: GET /api/users, header x-canary: true
       │
       │  Route 1: match headers x-canary=true AND uri=/api AND method=GET
       │           → ✅ 匹配! 转发到 subset v2
       │
       │  Route 2: (不检查了, 已命中)
```

### 2.2 DestinationRule

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
```

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews-dr
  namespace: production
spec:
  host: reviews.production.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30ms
        tcpKeepalive:
          time: 7200s
          interval: 75s
          probes: 9
      http:
        h2UpgradePolicy: DEFAULT
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        maxRetries: 3
        idleTimeout: 60s
        useClientProtocol: false

    loadBalancer:
      simple: LEAST_REQUEST
      # 或一致性哈希:
      # consistentHash:
      #   httpHeaderName: x-user-id
      #   # 或:
      #   # httpCookie:
      #   #   name: session
      #   #   ttl: 3600s
      #   # 或:
      #   # useSourceIp: true
      #   # 或:
      #   # maglev: {}

    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5

    tls:
      mode: ISTIO_MUTUAL
      # MUTUAL           - 用自己的证书
      # ISTIO_MUTUAL     - 用 Istio 自动管理的证书
      # SIMPLE           - 单向 TLS
      # PASSTHROUGH      - 透传 SNI
      # AUTO             - 自动检测

    portLevelSettings:
      - port:
          number: 8080
        connectionPool:
          http:
            h2UpgradePolicy: UPGRADE
        loadBalancer:
          simple: ROUND_ROBIN

  subsets:
    - name: v1
      labels:
        version: v1
      trafficPolicy:
        connectionPool:
          http:
            http2MaxRequests: 500
      # subset 级别的 trafficPolicy 覆盖顶层

    - name: v2
      labels:
        version: v2
```

**底层处理链路：**

```
DestinationRule YAML
    │
    ▼ istiod 解析
    │
    │  构建 DestinationRule 内部模型:
    │  ├── TrafficPolicy → Cluster 级别的 Envoy 配置
    │  ├── Subsets → 每个 subset 对应一个独立的 Envoy Cluster
    │  └── PortLevelSettings → 按端口覆盖默认策略
    │
    ▼ xDS 生成 (CDS)
    │
    │  为每个 subset × 每个 port 生成一个 Envoy Cluster:
    │
    │  Cluster: "outbound|8080||reviews.production.svc.cluster.local"
    │  Cluster: "outbound|8080|v1|reviews.production.svc.cluster.local"
    │  Cluster: "outbound|8080|v2|reviews.production.svc.cluster.local"
    │
    │  每个 Cluster 包含:
    │  ├── type: EDS
    │  ├── lb_policy: LEAST_REQUEST       ← loadBalancer
    │  ├── circuit_breakers:              ← connectionPool
    │  │   ├── thresholds.max_connections: 100
    │  │   ├── thresholds.max_pending_requests: 100
    │  │   └── thresholds.max_requests: 1000
    │  ├── outlier_detection:             ← outlierDetection
    │  │   ├── consecutive_5xx: 5
    │  │   ├── interval: 10s
    │  │   ├── base_ejection_time: 30s
    │  │   └── max_ejection_percent: 50
    │  ├── transport_socket:              ← tls
    │  │   ├── name: envoy.transport_sockets.tls
    │  │   └── tls_certificate_sds_config: "default"
    │  └── common_lb_config:              ← locality LB
    │      └── locality_weighted_lb_config: {}
    │
    ▼ Envoy 收到 Cluster 配置
    │
    │  创建 Cluster 对象:
    │  ├── 连接池参数 → 控制 upstream 连接行为
    │  ├── OutlierDetector → 定期检查 upstream 健康
    │  │   ├── 5xx 响应计数
    │  │   ├── 超时计数
    │  │   ├── 连续失败 → 触发 ejection
    │  │   └── ejection 期间 → 不分配流量
    │  └── LoadBalancer → 选择 endpoint
    │      ├── ROUND_ROBIN
    │      ├── LEAST_REQUEST
    │      ├── RANDOM
    │      └── RING_HASH (一致性哈希)
```

### 2.3 Gateway

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
```

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: production
spec:
  selector:
    istio: ingressgateway    # ← 绑定到哪个 Ingress Gateway Pod
  servers:
    - port:
        number: 443
        name: https
        protocol: HTTPS
      tls:
        mode: SIMPLE
        credentialName: my-tls-secret   # ← K8s Secret 或 istio CA
        minProtocolVersion: TLSV1_2
        cipherSuites:
          - ECDHE-RSA-AES256-GCM-SHA384
          - ECDHE-RSA-AES128-GCM-SHA256
      hosts:
        - "app.example.com"
        - "*.example.com"
      # SNI 匹配: *.example.com → 使用此证书

    - port:
        number: 80
        name: http
        protocol: HTTP
      tls:
        httpsRedirect: true     # HTTP → HTTPS 301 重定向
      hosts:
        - "app.example.com"
```

**底层处理链路：**

```
Gateway YAML
    │
    ▼ istiod 解析
    │
    │  1. selector 匹配:
    │     查找带有 label istio=ingressgateway 的 Pod
    │     (通过 Ingress Gateway Deployment 的 Pod template labels)
    │
    │  2. 构建 Listener 配置:
    │     每个 server.port → 一个 Envoy Listener
    │     每个 server.tls → Listener 的 TLS Context
    │
    ▼ xDS 生成 (LDS)
    │
    │  Listener: 0.0.0.0:443
    │  ├── filter_chain_match:
    │  │   ├── server_names: ["app.example.com", "*.example.com"]
    │  │   └── transport_protocol: "tls"
    │  ├── transport_socket:
    │  │   ├── common_tls_context:
    │  │   │   ├── tls_certificate_sds_secret_configs:
    │  │   │   │   ├── name: "kubernetes://my-tls-secret"
    │  │   │   │   └── sds_config: (从 K8s Secret 或 istiod SDS 获取)
    │  │   │   └── tls_params:
    │  │   │       ├── tls_minimum_protocol_version: TLSv1_2
    │  │   │       └── cipher_suites: [...]
    │  │   └── require_client_certificate: false (SIMPLE 模式)
    │  └── filters:
    │      └── HTTP Connection Manager
    │          └── route_config_name: "https.443.my-gateway.production"
    │
    │  Listener: 0.0.0.0:80
    │  └── filters:
    │      └── HTTP Connection Manager
    │          └── route:
    │              match: {prefix: "/"}
    │              redirect:
    │                https_redirect: true
    │                response_code: MOVED_PERMANENTLY (301)
    │
    ▼ Envoy (Ingress Gateway Pod) 收到配置
    │
    │  新增 443 端口的 Listener
    │  ├── TLS Inspector 嗅探 SNI
    │  ├── SNI 匹配 → 选择正确的证书
    │  ├── TLS 终止
    │  └── HTTP 路由
```

### 2.4 ServiceEntry

```yaml
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
```

```yaml
# 外部服务注册
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: production
spec:
  hosts:
    - api.external-service.com
  location: MESH_EXTERNAL
  ports:
    - number: 443
      name: https
      protocol: TLS
  resolution: DNS
  endpoints:
    - address: api.external-service.com
      ports:
        https: 443

# VM 工作负载注册
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: vm-service
  namespace: production
spec:
  hosts:
    - vm-app.production.svc.cluster.local
  location: MESH_INTERNAL
  ports:
    - number: 8080
      name: http
      protocol: HTTP
  resolution: STATIC
  endpoints:
    - address: 192.168.1.100
      labels:
        app: vm-app
        version: v1
      network: vm-network
```

**底层处理链路：**

```
ServiceEntry YAML
    │
    ▼ istiod 解析
    │
    │  将外部服务注册到内部 Service 模型:
    │  ├── host → Istio 内部 Service
    │  ├── endpoints → 内部 Endpoint 列表
    │  ├── location → MESH_EXTERNAL / MESH_INTERNAL
    │  └── resolution → DNS / STATIC / NONE
    │
    ▼ 影响的 xDS 配置:
    │
    │  CDS (Cluster):
    │  ├── type: STRICT_DNS (resolution=DNS)
    │  │   └── Envoy 自己做 DNS 解析
    │  ├── type: STATIC (resolution=STATIC)
    │  │   └── 直接使用 endpoints 中的 IP
    │  └── type: EDS (resolution=STATIC + 有 WorkloadEntry)
    │      └── 从 istiod 获取 endpoint 列表
    │
    │  EDS (Endpoint):
    │  ├── STATIC → 直接列出所有 endpoints 的 IP:Port
    │  └── DNS → Envoy 自己解析，不在 EDS 中
    │
    │  LDS (Listener):
    │  └── 为 ServiceEntry 的端口创建出站 Listener
    │
    ▼ Envoy 收到配置
    │
    │  Cluster: "outbound|443||api.external-service.com"
    │  ├── type: STRICT_DNS
    │  ├── dns_lookup_family: V4_ONLY
    │  └── load_assignment:
    │      endpoints:
    │        - address: api.external-service.com:443
    │
    │  Envoy 定期解析 DNS:
    │  ├── dns_refresh_rate: 5s (默认)
    │  ├── 支持 DNS failover
    │  └── IP 变化时自动更新 endpoint
```

### 2.5 Sidecar

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Sidecar
```

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Sidecar
metadata:
  name: default
  namespace: production
spec:
  workloadSelector:
    labels:
      app: my-app
  egress:
    # 只允许访问这些服务
    - hosts:
        - "production/*"              # 本 namespace 的所有服务
        - "istio-system/istiod.istio-system.svc.cluster.local"
        - "monitoring/*"              # 监控 namespace
      port:
        number: 9080
        protocol: HTTP
        name: http

    - hosts:
        - "external-api.com"          # 外部服务
      port:
        number: 443
        protocol: TLS

  ingress:
    - port:
        number: 8080
        protocol: HTTP
      defaultEndpoint: 127.0.0.1:8080  # 转发到 localhost
      # capture 模式下默认就是 localhost

    - port:
        number: 15006
        protocol: HTTP
      defaultEndpoint: 127.0.0.1:15006

  outboundTrafficPolicy:
    mode: REGISTRY_ONLY    # 只允许访问注册的服务
    # mode: ALLOW_ANY      # 允许访问任意外部地址
```

**底层处理链路：**

```
Sidecar YAML
    │
    ▼ istiod 解析
    │
    │  Sidecar 的核心作用: 限制 Envoy 的配置范围
    │
    │  1. workloadSelector 匹配:
    │     查找 label app=my-app 的 Pod
    │     该 Pod 的 Envoy 只收到受限的 xDS 配置
    │
    │  2. egress.hosts 过滤:
    │     Envoy 只会收到这些 Service 的 CDS/EDS/RDS
    │     其他 Service 的配置不推送给该 Pod
    │     → 减少 Envoy 内存占用和配置同步时间
    │
    │  3. outboundTrafficPolicy:
    │     REGISTRY_ONLY → 未注册的 Service 返回 502
    │     ALLOW_ANY    → 未注册的 Service 直接通过
    │
    ▼ xDS 生成差异
    │
    │  没有 Sidecar CR:
    │  Envoy 收到集群中所有 Service 的配置
    │  10000 个 Service → 10000 个 Cluster → 大量内存
    │
    │  有 Sidecar CR:
    │  Envoy 只收到 egress.hosts 中列出的 Service
    │  50 个 Service → 50 个 Cluster → 节省内存
    │
    │  Envoy Listener 变化:
    │  ├── virtual outbound Listener (15001)
    │  │   └── 只为受限范围的 Service 配置路由
    │  │
    │  └── virtual inbound Listener (15006)
    │      └── ingress 规则决定接收哪些端口
    │
    ▼ Envoy 收到精简后的配置
    │
    │  内存占用:
    │  ├── 没有 Sidecar: 100MB (10000 个 Service)
    │  └── 有 Sidecar:   30MB  (50 个 Service)
    │
    │  xDS 推送延迟:
    │  ├── 没有 Sidecar: 每次推送所有 Service 变更
    │  └── 有 Sidecar:   只推送相关 Service 变更
```

### 2.6 WorkloadEntry + WorkloadGroup

```yaml
apiVersion: networking.istio.io/v1beta1
kind: WorkloadEntry
```

```yaml
# WorkloadEntry: 将 VM/物理机注册为网格工作负载
apiVersion: networking.istio.io/v1beta1
kind: WorkloadEntry
metadata:
  name: vm-server-1
  namespace: production
spec:
  address: 192.168.1.100
  labels:
    app: legacy-app
    version: v1
  serviceAccount: legacy-app-sa
  network: vm-network
  ports:
    http: 8080

---
# WorkloadGroup: VM 工作负载的模板 (类似 Deployment for Pods)
apiVersion: networking.istio.io/v1beta1
kind: WorkloadGroup
metadata:
  name: legacy-app
  namespace: production
spec:
  metadata:
    labels:
      app: legacy-app
  template:
    serviceAccount: legacy-app-sa
    network: vm-network
  probe:
    httpGet:
      path: /healthz
      port: 8080
    initialDelaySeconds: 5
    periodSeconds: 10
```

**底层处理链路：**

```
WorkloadEntry + ServiceEntry 组合使用:

ServiceEntry:
  hosts: [legacy-app.production.svc.cluster.local]
  resolution: STATIC
  endpoints:
    - address: 192.168.1.100    # 直接指定
    # 或引用 WorkloadEntry:
    - name: vm-server-1         # 引用 WorkloadEntry

    │
    ▼ istiod
    │
    │  ServiceEntry 定义服务
    │  WorkloadEntry 提供 endpoint 详情
    │  组合后:
    │  ├── Service: legacy-app.production.svc.cluster.local
    │  └── Endpoints:
    │      ├── 192.168.1.100:8080 (WorkloadEntry: vm-server-1)
    │      └── 192.168.1.101:8080 (WorkloadEntry: vm-server-2)
    │
    ▼ xDS
    │
    │  CDS: Cluster for legacy-app
    │  EDS: Endpoints [192.168.1.100, 192.168.1.101]
    │
    ▼ VM 上的 Envoy (通过 istioctl x workload entry configure 安装)
    │
    │  VM 的 Envoy 启动:
    │  ├── Bootstrap: 连接 istiod
    │  ├── SDS: 获取证书
    │  ├── LDS/CDS/RDS/EDS: 获取配置
    │  └── 通过 ServiceEntry 的 address 注册自己为 endpoint


WorkloadGroup 的自动生成:

istioctl x workload entry configure \
  --name legacy-app \
  --namespace production \
  --outputDir ./vm-config

生成:
├── envoy.yaml          (Bootstrap 配置)
├── root-cert.pem       (Root CA)
├── cluster.env         (集群配置)
└── istio-token         (ServiceAccount Token)

VM 上安装:
├── 安装 Envoy sidecar
├── 加载 bootstrap 配置
├── 自动注册 WorkloadEntry
└── 连接 istiod 接收配置
```

### 2.7 EnvoyFilter (高级)

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: custom-header
  namespace: istio-system     # 全局生效
  # 或 specific namespace
spec:
  workloadSelector:
    labels:
      istio: ingressgateway

  configPatches:
    # Patch 1: 在 HTTP Connection Manager 中添加 filter
    - applyTo: HTTP_FILTER
      match:
        context: GATEWAY        # 只影响 Gateway
        listener:
          filterChain:
            filter:
              name: "envoy.filters.network.http_connection_manager"
              subFilter:
                name: "envoy.filters.http.router"
      patch:
        operation: INSERT_BEFORE
        value:
          name: "envoy.filters.http.lua"
          typed_config:
            "@type": "type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua"
            inlineCode: |
              function envoy_on_request(request_handle)
                local header = request_handle:headers():get("x-custom")
                if header then
                  request_handle:headers():add("x-processed", "true")
                end
              end

    # Patch 2: 修改 Cluster 超时
    - applyTo: CLUSTER
      match:
        context: SIDECAR_OUTBOUND
        cluster:
          name: "outbound|8080||my-app.production.svc.cluster.local"
      patch:
        operation: MERGE
        value:
          connect_timeout: "5s"
          circuit_breakers:
            thresholds:
              - max_connections: 200

    # Patch 3: 添加 Listener filter
    - applyTo: LISTENER
      match:
        context: SIDECAR_INBOUND
        listener:
          portNumber: 8080
      patch:
        operation: ADD
        value:
          name: "custom_filter"
          typed_config:
            "@type": "type.googleapis.com/..."
```

**底层处理链路：**

```
EnvoyFilter YAML
    │
    ▼ istiod 解析
    │
    │  EnvoyFilter 是"最后手段"的配置工具
    │  直接操作 Envoy 的底层配置结构
    │
    │  处理顺序:
    │  1. 先生成正常的 xDS 配置 (基于 VS/DR/GW/SE 等)
    │  2. 然后应用 EnvoyFilter patches
    │     ├── applyTo 决定 patch 目标类型:
    │     │   ├── LISTENER      → 修改 Listener
    │     │   ├── FILTER_CHAIN  → 修改 Filter Chain
    │     │   ├── NETWORK_FILTER → 修改 Network Filter
    │     │   ├── HTTP_FILTER    → 修改 HTTP Filter
    │     │   ├── CLUSTER       → 修改 Cluster
    │     │   ├── ROUTE_CONFIGURATION → 修改 Route
    │     │   ├── VIRTUAL_HOST  → 修改 VirtualHost
    │     │   └── BOOTSTRAP     → 修改 Bootstrap
    │     │
    │     ├── operation 决定操作类型:
    │     │   ├── ADD          → 追加新配置
    │     │   ├── INSERT_BEFORE → 在指定 filter 前插入
    │     │   ├── INSERT_AFTER  → 在指定 filter 后插入
    │     │   ├── REMOVE        → 删除匹配的配置
    │     │   └── MERGE         → 合并到现有配置
    │     │
    │     └── match 条件过滤:
    │         ├── context: ANY/SIDECAR_INBOUND/SIDECAR_OUTBOUND/GATEWAY
    │         ├── listener: 端口/协议/filterChain 匹配
    │         ├── cluster: 名称/端口/host 匹配
    │         └── routeConfiguration: 名称/端口/host 匹配
    │
    ▼ xDS 最终输出
    │
    │  正常配置 + EnvoyFilter patches = 最终 Envoy 配置
    │
    ▼ Envoy 收到配置

⚠️ 警告:
├── EnvoyFilter 直接操作 Envoy 内部结构
├── 没有 schema 验证 (错误配置会导致 Envoy 拒绝)
├── Envoy 版本升级可能破坏 EnvoyFilter
├── 优先使用标准 CRD，只在万不得已时使用 EnvoyFilter
└── 不同 EnvoyFilter 之间的执行顺序不确定
```

### 2.8 ProxyConfig

```yaml
apiVersion: networking.istio.io/v1beta1
kind: ProxyConfig
```

```yaml
apiVersion: networking.istio.io/v1beta1
kind: ProxyConfig
metadata:
  name: my-app-proxy-config
  namespace: production
spec:
  selector:
    matchLabels:
      app: my-app
  concurrency: 4
  image:
    imageType: envoy              # 默认 Envoy
  environmentVariables:
    PROXY_XDS_VIA_AGENT: "true"
  drainDuration: 30s
  holdApplicationUntilProxyStarts: true
```

**底层处理链路：**

```
ProxyConfig YAML
    │
    ▼ istiod 解析
    │
    │  ProxyConfig 覆盖全局 proxy 配置
    │  作用域: workloadSelector 匹配的 Pod
    │
    │  影响:
    │  ├── Envoy 启动参数 (--concurrency)
    │  ├── Envoy Bootstrap 配置
    │  ├── Pod 启动顺序 (holdApplicationUntilProxyStarts)
    │  └── 环境变量注入
    │
    ▼ 注入到 Pod spec 中
    │
    │  生成的 Pod spec:
    │  containers:
    │    - name: istio-proxy
    │      args:
    │        - --concurrency=4        ← concurrency
    │        - --drainDuration=30s    ← drainDuration
    │      env:
    │        - name: PROXY_XDS_VIA_AGENT
    │          value: "true"          ← environmentVariables
    │
    ▼ sidecar 注入 webhook 使用此配置
```

---

## 三、security.istio.io — 安全策略

### 3.1 PeerAuthentication

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
```

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT

  selector:
    matchLabels:
      app: backend

  portLevelMtls:
    8080:
      mode: STRICT
    9090:
      mode: PERMISSIVE    # 健康检查端口允许明文
```

**底层处理链路：**

```
PeerAuthentication YAML
    │
    ▼ istiod 解析
    │
    │  PeerAuthentication 决定入站 TLS 策略
    │  优先级: portLevel > workload > namespace > mesh default
    │
    │  mode 含义:
    │  ├── STRICT: 只接受 mTLS 连接
    │  ├── PERMISSIVE: 同时接受 mTLS 和明文
    │  └── DISABLE: 禁用 mTLS (不推荐)
    │
    ▼ xDS 生成
    │
    │  STRICT 模式 → Envoy Listener 配置:
    │  Listener: 0.0.0.0:8080
    │  ├── filter_chains:
    │  │   └── transport_socket:
    │  │       ├── name: "envoy.transport_sockets.tls"
    │  │       └── require_client_certificate: true
    │  │           common_tls_context:
    │  │             validation_context:
    │  │               trusted_ca: { ... }    # 验证客户端证书
    │  │
    │  非 TLS 连接 → TLS Inspector 检测到 → 匹配失败 → 连接拒绝
    │
    │  PERMISSIVE 模式 → Envoy Listener 配置:
    │  Listener: 0.0.0.0:8080
    │  ├── filter_chains:
    │  │   ├── # Chain 1: TLS 连接
    │  │   │   transport_protocol: "tls"
    │  │   │   transport_socket: { TLS 配置 }
    │  │   │   → 走 mTLS 路径
    │  │   │
    │  │   └── # Chain 2: 明文连接
    │  │       transport_protocol: "raw_buffer"
    │  │       → 走明文路径 (无 TLS)
    │  │
    │  Envoy 根据 transport_protocol 选择 filter chain:
    │  ├── TLS Inspector 检测到 TLS → 选择 Chain 1
    │  └── 检测到明文 → 选择 Chain 2
```

### 3.2 RequestAuthentication

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
```

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: production
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
    - issuer: "https://auth.example.com"
      jwksUri: "https://auth.example.com/.well-known/jwks.json"
      audiences:
        - "my-app"
      forwardOriginalToken: true
      outputPayloadToHeader: "x-jwt-payload"
      fromHeaders:
        - name: Authorization
          prefix: "Bearer "
        - name: x-custom-token
      fromParams:
        - "token"
      outputClaimToHeaders:
        - header: "x-jwt-sub"
          claim: "sub"
        - header: "x-jwt-email"
          claim: "email"
```

**底层处理链路：**

```
RequestAuthentication YAML
    │
    ▼ istiod 解析
    │
    │  生成 Envoy JWT Provider 配置
    │
    ▼ xDS 生成 (ECDS 或嵌入 HCM)
    │
    │  HTTP Filter: envoy.filters.http.jwt_authn
    │
    │  providers:
    │    "https://auth.example.com":
    │      issuer: "https://auth.example.com"
    │      audiences: ["my-app"]
    │      remote_jwks:
    │        http_uri:
    │          uri: "https://auth.example.com/.well-known/jwks.json"
    │          cluster: "outbound|443||auth.example.com"
    │        cache_duration: 300s        # JWKS 缓存 5 分钟
    │        async_fetch:                # 异步预取 JWKS
    │          enabled: true
    │      forward: true                 # forwardOriginalToken
    │      payload_in_metadata: "jwt_payload"
    │      from_headers:
    │        - name: Authorization
    │          value_prefix: "Bearer "
    │      from_params: ["token"]
    │      output_claim_to_headers:
    │        - header_name: "x-jwt-sub"
    │          claim_name: "sub"
    │
    ▼ Envoy JWT Filter 执行流程
    │
    │  请求到达:
    │  1. 提取 JWT token
    │     ├── 从 header: Authorization: Bearer eyJhbG...
    │     ├── 或 fromParams: ?token=eyJhbG...
    │     └── 或 fromHeaders: x-custom-token: eyJhbG...
    │
    │  2. 解码 JWT
    │     ├── Base64 解码 header: {"alg":"RS256","kid":"abc"}
    │     ├── Base64 解码 payload: {"iss":"...","aud":"my-app","sub":"user1"}
    │     └── 验证签名 (使用 JWKS 公钥)
    │
    │  3. 验证 claims
    │     ├── issuer 匹配 → ✅
    │     ├── audience 包含 "my-app" → ✅
    │     └── expiration > now → ✅
    │
    │  4. 设置 metadata (供后续 RBAC filter 使用)
    │     jwt_payload: {iss, aud, sub, email, ...}
    │
    │  5. 添加 output headers
    │     x-jwt-sub: user1
    │     x-jwt-email: user@example.com
    │
    │  6. 如果验证失败:
    │     └── 返回 401 Unauthorized (除非是可选的)
    │
    │  ⚠️ RequestAuthentication 单独不会拒绝请求!
    │     只做验证和提取 claims
    │     拒绝需要配合 AuthorizationPolicy
```

### 3.3 AuthorizationPolicy

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
```

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-authz
  namespace: production
spec:
  selector:
    matchLabels:
      app: backend

  # ALLOW 策略
  action: ALLOW
  rules:
    # 规则 1: 允许 frontend 访问 GET /api/*
    - from:
        - source:
            principals:
              - "cluster.local/ns/production/sa/frontend-sa"
            namespaces:
              - "production"
            ipBlocks:
              - "10.244.0.0/16"
            requestPrincipals:
              - "https://auth.example.com/user1"
      to:
        - operation:
            methods: ["GET"]
            paths: ["/api/*"]
            ports: ["8080"]
      when:
        - key: request.headers[x-api-key]
          values: ["secret-*"]
          notValues: ["invalid-*"]
        - key: source.namespace
          values: ["production"]
          notValues: ["test"]
        - key: request.auth.claims[groups]
          values: ["admin"]

    # 规则 2: 允许健康检查
    - to:
        - operation:
            methods: ["GET"]
            paths: ["/healthz"]
            ports: ["15020"]

  # DENY 策略 (如果 action=DENY)
  # action: DENY
  # rules:
  #   - from:
  #       - source:
  #           notNamespaces: ["istio-system"]

  # CUSTOM 策略 (调用外部授权服务)
  # action: CUSTOM
  # provider:
  #   name: "ext-authz"
```

**底层处理链路：**

```
AuthorizationPolicy YAML
    │
    ▼ istiod 解析
    │
    │  策略合并逻辑:
    │  ├── ALLOW 策略: 任意一条规则匹配 → 允许
    │  ├── DENY 策略: 任意一条规则匹配 → 拒绝
    │  ├── CUSTOM 策略: 调用外部授权服务
    │  └── 执行顺序: CUSTOM → DENY → ALLOW
    │      (没有 ALLOW 策略 → 默认拒绝)
    │
    ▼ xDS 生成
    │
    │  HTTP Filter: envoy.filters.http.rbac
    │
    │  RBAC 配置:
    │  {
    │    "rules": {
    │      "policies": {
    │        "backend-authz": {         // 策略名称
    │          "permissions": [          // to 规则
    │            {
    │              "and_rules": {
    │                "rules": [
    │                  {"header": { "name": ":method", "exact_match": "GET" }},
    │                  {"url_path": {"path": {"prefix": "/api/"}}},
    │                  {"destination_port": 8080}
    │                ]
    │              }
    │            },
    │            // 健康检查规则 (OR 关系)
    │            {
    │              "and_rules": {
    │                "rules": [
    │                  {"header": { "name": ":method", "exact_match": "GET" }},
    │                  {"url_path": {"path": {"exact": "/healthz"}}},
    │                  {"destination_port": 15020}
    │                ]
    │              }
    │            }
    │          ],
    │          "principals": [           // from 规则
    │            {
    │              "and_ids": {
    │                "ids": [
    │                  {"authenticated": {
    │                    "principal_name": {
    │                      "exact": "cluster.local/ns/production/sa/frontend-sa"
    │                    }
    │                  }},
    │                  {"source_ip": {"address_prefix": "10.244.0.0", "prefix_len": 16}}
    │                ]
    │              }
    │            }
    │          ],
    │          "conditions": [           // when 规则
    │            {
    │              "key": "request.headers[x-api-key]",
    │              "values": ["secret-*"]
    │            }
    │          ]
    │        }
    │      }
    │    }
    │  }
    │
    ▼ Envoy RBAC Filter 执行流程
    │
    │  请求到达时:
    │
    │  1. 检查 DENY 策略
    │     └── 匹配 → 拒绝 (403 Forbidden)
    │
    │  2. 检查 CUSTOM 策略
    │     └── 调用外部服务 → 允许/拒绝
    │
    │  3. 检查 ALLOW 策略
    │     ├── 解析请求:
    │     │   ├── source.principal ← mTLS 证书中的 SPIFFE ID
    │     │   ├── source.namespace ← HBONE metadata 或证书
    │     │   ├── source.ip ← 连接的源 IP
    │     │   ├── request.auth.principal ← JWT 中的 iss/sub
    │     │   ├── request.headers ← HTTP headers
    │     │   ├── request.method ← :method header
    │     │   ├── request.url_path ← :path header
    │     │   ├── destination.port ← 连接的目标端口
    │     │   └── metadata ← Envoy 动态元数据
    │     │
    │     ├── 匹配 from 规则:
    │     │   principals 中任意一个匹配 (OR)
    │     │   每个 principal 内部的 ids 全部匹配 (AND)
    │     │
    │     ├── 匹配 to 规则:
    │     │   permissions 中任意一个匹配 (OR)
    │     │   每个 permission 内部的 rules 全部匹配 (AND)
    │     │
    │     ├── 匹配 when 条件:
    │     │   所有条件都匹配 (AND)
    │     │
    │     └── 全部匹配 → ALLOW
    │         无匹配 → 隐式拒绝
    │
    │  4. 如果没有 ALLOW 策略定义:
    │     └── 默认允许 (重要!)
```

---

## 四、telemetry.istio.io — 遥测配置

### 4.1 Telemetry

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-defaults
  namespace: istio-system      # mesh 级别
spec:
  # 指标配置
  metrics:
    - providers:
        - name: prometheus
      overrides:
        - match:
            mode: CLIENT_AND_SERVER
            metric: ALL_METRICS
          tagOverrides:
            request_host:
              operation: UPSERT
              value: "request.host"
        - match:
            metric: REQUEST_COUNT
          disabled: false

    - providers:
        - name: otel
      overrides:
        - match:
            metric: REQUEST_DURATION
          tagOverrides:
            response_code:
              operation: REMOVE

  # 访问日志配置
  accessLogging:
    - providers:
        - name: otel
      filter:
        expression: "response.code >= 400"
      match:
        mode: CLIENT_AND_SERVER

    - providers:
        - name: envoy
      filter:
        expression: "true"

  # 分布式追踪配置
  tracing:
    - providers:
        - name: zipkin
      randomSamplingPercentage: 10.0
      customTags:
        environment:
          literal:
            value: "production"
        cluster:
          environment:
            name: "CLUSTER_NAME"
        request_id:
          header:
            name: x-request-id
            defaultValue: "unknown"
```

**底层处理链路：**

```
Telemetry YAML
    │
    ▼ istiod 解析
    │
    │  作用域确定 (优先级从高到低):
    │  1. workload selector (如果指定)
    │  2. namespace 级别
    │  3. mesh 级别 (istio-system namespace)
    │
    │  合并多层 Telemetry 配置:
    │  mesh 级别 + namespace 级别 + workload 级别
    │  更具体的覆盖更一般的
    │
    ▼ xDS 生成
    │
    │  指标 → Envoy Stats Filter 配置:
    │  ├── metrics_providers:
    │  │   └── prometheus: { ... }
    │  └── stat_prefix / dimensions / tags
    │
    │  访问日志 → Envoy Access Log 配置:
    │  ├── HCM.access_log:
    │  │   ├── provider: otel
    │  │   │   grpc_service:
    │  │   │     envoy_grpc:
    │  │   │       cluster_name: "otel-collector"
    │  │   │   body: { ... }
    │  │   │   filter:
    │  │   │     status_code_filter:
    │  │   │       comparison:
    │  │   │         ge: 400       # response.code >= 400
    │  │   └── provider: envoy
    │  │       file:
    │  │         path: "/dev/stdout"
    │
    │  追踪 → Envoy Tracing 配置:
    │  ├── HCM.tracing:
    │  │   provider:
    │  │     name: envoy.tracers.zipkin
    │  │   random_sampling: 0.1    # 10%
    │  │   custom_tags:
    │  │     environment: { literal: "production" }
    │  │     cluster: { environment: "CLUSTER_NAME" }
    │  │     request_id: { request_header: "x-request-id" }
```

---

## 五、extensions.istio.io — Wasm 扩展

### 5.1 WasmPlugin

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
```

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: rate-limiter
  namespace: production
spec:
  selector:
    matchLabels:
      app: backend

  # 插件在 filter chain 中的位置
  phase: AUTHN           # AUTHN / AUTHZ / STATS
  # AUTHN → 在 JWT 验证之后, RBAC 之前
  # AUTHZ → 在 RBAC 之后
  # STATS → 在统计收集阶段

  url: "oci://ghcr.io/my-org/rate-limiter:1.0.0"
  # 或:
  # url: "file:///opt/wasm/rate-limiter.wasm"
  # url: "https://example.com/rate-limiter.wasm"

  sha256: "abc123..."

  pluginConfig:
    max_requests_per_second: 100
    burst_size: 20
    key: "request.headers[x-api-key]"

  imagePullPolicy: IfNotPresent
  imagePullSecret: my-registry-secret

  vmConfig:
    env:
      - name: LOG_LEVEL
        value: "info"
```

**底层处理链路：**

```
WasmPlugin YAML
    │
    ▼ istiod 解析
    │
    │  确定 Wasm 插件在 Envoy filter chain 中的位置:
    │  ├── phase: AUTHN → 在 authn filter 之后
    │  │   └── HTTP filter 顺序:
    │  │       ... → JWT Authn → WasmPlugin(rate-limiter) → RBAC → Router
    │  │
    │  ├── phase: AUTHZ → 在 rbac filter 之后
    │  │   └── HTTP filter 顺序:
    │  │       ... → JWT Authn → RBAC → WasmPlugin(rate-limiter) → Router
    │  │
    │  └── phase: STATS → 在 stats filter 之前
    │      └── HTTP filter 顺序:
    │          ... → RBAC → WasmPlugin → Stats → Router
    │
    ▼ xDS 生成
    │
    │  HTTP Filter: envoy.filters.http.wasm
    │
    │  {
    │    "name": "envoy.filters.http.wasm",
    │    "typed_config": {
    │      "@type": "type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm",
    │      "config": {
    │        "name": "rate-limiter",
    │        "root_id": "rate-limiter",
    │        "vm_config": {
    │          "runtime": "envoy.wasm.runtime.v8",    // V8 引擎
    │          "code": {
    │            "remote": {
    │              "http_uri": {
    │                "uri": "oci://ghcr.io/my-org/rate-limiter:1.0.0",
    │                "cluster": "_wasm_oci_cluster"
    │              },
    │              "sha256": "abc123..."
    │            }
    │          },
    │          "environment_variables": {
    │            "key_values": {
    │              "LOG_LEVEL": "info"
    │            }
    │          }
    │        },
    │        "configuration": {
    │          "@type": "type.googleapis.com/google.protobuf.Any",
    │          "value": <pluginConfig protobuf encoded>
    │        }
    │      }
    │    }
    │  }
    │
    ▼ Envoy 收到配置
    │
    │  1. 下载 Wasm 二进制
    │     ├── OCI registry → 拉取镜像 → 提取 .wasm 文件
    │     ├── HTTP URL → 直接下载
    │     └── file:// → 从本地路径读取
    │
    │  2. 验证 SHA256
    │
    │  3. 初始化 Wasm VM
    │     ├── V8 runtime: 加载 .wasm 到 V8 isolate
    │     ├── 或 Wasmtime runtime
    │     ├── 分配内存
    │     └── 调用 _start / _initialize
    │
    │  4. 每个请求的执行:
    │     ├── onRequestHeaders(headers, end_of_stream)
    │     │   └── Wasm 代码可以读取/修改 headers
    │     ├── onRequestBody(body, end_of_stream)
    │     │   └── 读取/修改请求体
    │     ├── onResponseHeaders(headers, end_of_stream)
    │     ├── onResponseBody(body, end_of_stream)
    │     └── Wasm 可以:
    │         ├── 修改 headers
    │         ├── 返回自定义响应 (拦截)
    │         ├── 读取/写入共享数据
    │         └── 记录指标
    │
    ▼ 性能影响
    │
    │  Wasm 每次调用的开销:
    │  ├── V8 JIT 编译后: ~1-10μs per call
    │  ├── 冷启动: ~100ms (首次加载 + 编译)
    │  └── 内存: ~5-10MB per VM
    │
    │  对比 Lua filter:
    │  ├── Lua: ~0.5-5μs per call (解释执行)
    │  └── Wasm: ~1-10μs per call (JIT 编译后)
    │  差距很小，但 Wasm 更安全 (沙箱隔离)
```

---

## 六、install.istio.io — 安装管理

### 6.1 IstioOperator

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
```

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: installed-state        # 自动创建，记录安装状态
  namespace: istio-system
spec:
  profile: default
  hub: docker.io/istio
  tag: 1.22.0
  meshConfig:
    ...
  components:
    ...
  values:
    ...
```

**底层处理链路：**

```
IstioOperator YAML
    │
    ▼ istio-operator (istiod 内置或独立进程)
    │
    │  istioctl install 或 kubectl apply 都会触发:
    │
    │  1. 读取 IstioOperator CR
    │  2. 加载 Profile → 合并 overlay
    │  3. 渲染 Helm templates
    │  4. 生成 K8s manifests
    │  5. Server-side apply 到集群
    │
    ▼ 生成的 K8s 资源:
    │
    │  ├── CRDs (base chart)
    │  ├── Deployment: istiod
    │  ├── Service: istiod
    │  ├── ConfigMap: istio (mesh config)
    │  ├── ConfigMap: istio-sidecar-injector
    │  ├── ServiceAccount: istiod
    │  ├── ClusterRole: istiod
    │  ├── ClusterRoleBinding: istiod
    │  ├── ValidatingWebhookConfiguration
    │  ├── MutatingWebhookConfiguration
    │  ├── Deployment: istio-ingressgateway (如果启用)
    │  ├── Service: istio-ingressgateway
    │  ├── HorizontalPodAutoscaler: istiod
    │  ├── PodDisruptionBudget: istiod
    │  └── ...
    │
    ▼ 同时创建 IstioOperator CR: "installed-state"
       记录当前安装的最终配置 (用于 istioctl upgrade 对比)
```

---

## 七、apiVersion 的演进历史

```
Istio CRD API 版本演进:

┌───────────────┬────────────────────────────────────────────────────┐
│  版本          │  说明                                              │
├───────────────┼────────────────────────────────────────────────────┤
│  v1alpha1     │  最早的实验版本                                      │
│               │  已大部分迁移走                                      │
│               │  EnvoyFilter 仍然在此版本 (稳定但不推荐频繁使用)      │
│               │  IstioOperator 仍然在此版本 (安装专用)               │
│               │  WasmPlugin 在此版本                                │
├───────────────┼────────────────────────────────────────────────────┤
│  v1alpha2     │  过渡版本，很少使用                                   │
├───────────────┼────────────────────────────────────────────────────┤
│  v1alpha3     │  networking.istio.io 的主要版本                      │
│               │  VirtualService, DestinationRule, Gateway           │
│               │  ServiceEntry, Sidecar, WorkloadEntry               │
│               │  WorkloadGroup, EnvoyFilter                        │
│               │  虽然叫 alpha3，但大部分已经是 GA 状态               │
├───────────────┼────────────────────────────────────────────────────┤
│  v1beta1      │  networking.istio.io 的新版本                       │
│               │  VirtualService, DestinationRule 等已迁移至此        │
│               │  与 v1alpha3 schema 完全相同                        │
│               │  ProxyConfig 在此版本                               │
├───────────────┼────────────────────────────────────────────────────┤
│  v1           │  security.istio.io 的 GA 版本                       │
│               │  AuthorizationPolicy (v1beta1 → v1)                │
│               │  PeerAuthentication                                │
│               │  RequestAuthentication                             │
│               │  telemetry.istio.io/v1 (Telemetry)                 │
│               │  extensions.istio.io/v1alpha1 (WasmPlugin)         │
└───────────────┴────────────────────────────────────────────────────┘
```

```bash
# 查看 CRD 的所有版本
kubectl get crd virtualservices.networking.istio.io \
  -o jsonpath='{.spec.versions[*].name}'

# 输出: v1alpha3 v1beta1

# 查看存储版本 (etcd 中实际存储的版本)
kubectl get crd virtualservices.networking.istio.io \
  -o jsonpath='{.spec.versions[?(@.storage==true)].name}'

# 输出: v1beta1

# 查看某个版本是否已废弃
kubectl get crd virtualservices.networking.istio.io \
  -o jsonpath='{.spec.versions[?(@.name=="v1alpha3")].deprecated}'

# 输出: true
```

---

## 八、CRD 到 xDS 的完整映射总表

```
┌──────────────────────────┬──────────────┬────────────────────────────────────┐
│  Istio CRD               │  xDS 资源    │  Envoy 内部对象                     │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  VirtualService          │  RDS         │  RouteConfiguration                │
│  (HTTP rules)            │              │  ├── VirtualHost                   │
│                          │              │  │   └── Route                     │
│                          │              │  │       ├── match (path/header)   │
│                          │              │  │       ├── route (cluster/weight)│
│                          │              │  │       ├── fault (delay/abort)   │
│                          │              │  │       ├── retry                 │
│                          │              │  │       ├── timeout               │
│                          │              │  │       ├── mirror                │
│                          │              │  │       └── cors                  │
│                          │              │  └── ...
│                          │              │                                    │
│  VirtualService          │  LDS         │  Listener                         │
│  (TCP rules)             │              │  └── FilterChain                  │
│                          │              │      └── TcpProxy                 │
│                          │              │          └── cluster              │
│                          │              │                                    │
│  VirtualService          │  LDS         │  Listener                         │
│  (TLS rules)             │              │  └── FilterChain                  │
│                          │              │      └── TcpProxy (SNI routing)   │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  DestinationRule         │  CDS         │  Cluster                          │
│  (trafficPolicy)         │              │  ├── type: EDS/STRICT_DNS/STATIC  │
│                          │              │  ├── lb_policy                     │
│                          │              │  ├── circuit_breakers              │
│                          │              │  ├── outlier_detection             │
│                          │              │  ├── connection_pool               │
│                          │              │  └── transport_socket (TLS)        │
│                          │              │                                    │
│  DestinationRule         │  CDS         │  Cluster (per subset)             │
│  (subsets)               │              │  name: outbound|port|subset|host  │
│                          │              │                                    │
│  DestinationRule         │  EDS         │  ClusterLoadAssignment            │
│  (subsets → endpoints)   │              │  ├── locality                     │
│                          │              │  ├── lb_endpoints                 │
│                          │              │  │   ├── endpoint (IP:port)       │
│                          │              │  │   └── metadata (subset labels) │
│                          │              │  └── priority/weight              │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  Gateway                 │  LDS         │  Listener                         │
│                          │              │  ├── address: 0.0.0.0:443         │
│                          │              │  ├── filter_chains:               │
│                          │              │  │   ├── server_names (SNI)       │
│                          │              │  │   ├── transport_socket (TLS)   │
│                          │              │  │   └── HCM filter              │
│                          │              │  └── per_server_port → Listener  │
│                          │              │                                    │
│  Gateway                 │  RDS         │  RouteConfiguration               │
│  (VirtualService binding)│              │  绑定的 VirtualService 路由       │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  ServiceEntry            │  CDS         │  Cluster                          │
│                          │              │  type: STRICT_DNS / STATIC        │
│                          │              │                                    │
│  ServiceEntry            │  EDS         │  ClusterLoadAssignment            │
│                          │              │  (STATIC resolution)              │
│                          │              │                                    │
│  ServiceEntry            │  LDS         │  Listener (outbound)              │
│                          │              │  为 external service 创建出站监听  │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  Sidecar                 │  LDS         │  Listener (受限范围)               │
│                          │              │  只包含 egress.hosts 中的服务      │
│                          │              │                                    │
│  Sidecar                 │  RDS/CDS/EDS │  只推送匹配的资源                  │
│                          │              │  减少 Envoy 配置量                 │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  PeerAuthentication      │  LDS         │  Listener                         │
│                          │              │  transport_socket                  │
│                          │              │  ├── STRICT: require_client_cert   │
│                          │              │  └── PERMISSIVE: dual filter chain│
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  RequestAuthentication   │  HCM         │  HTTP Filter                      │
│                          │ (嵌入)        │  envoy.filters.http.jwt_authn    │
│                          │              │  ├── providers                     │
│                          │              │  └── rules (route → provider)     │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  AuthorizationPolicy     │  HCM/Network │  HTTP/Network Filter              │
│                          │ (嵌入)        │  envoy.filters.http.rbac          │
│                          │              │  ├── ALLOW policies               │
│                          │              │  ├── DENY policies                │
│                          │              │  └── CUSTOM (ext_authz)           │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  Telemetry               │  HCM         │  HTTP Filter                      │
│  (metrics)               │ (嵌入)        │  istio.stats (Prometheus)         │
│                          │              │                                    │
│  Telemetry               │  HCM         │  access_log 配置                  │
│  (accessLogging)         │ (嵌入)        │  ├── file (stdout)               │
│                          │              │  └── grpc (otel-collector)        │
│                          │              │                                    │
│  Telemetry               │  HCM         │  tracing 配置                     │
│  (tracing)               │ (嵌入)        │  ├── provider (zipkin/jaeger)    │
│                          │              │  ├── sampling rate                │
│                          │              │  └── custom_tags                  │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  WasmPlugin              │  HCM         │  HTTP Filter                      │
│                          │ (嵌入)        │  envoy.filters.http.wasm          │
│                          │              │  ├── vm_config (V8/Wasmtime)      │
│                          │              │  ├── code (OCI/HTTP/file)         │
│                          │              │  └── configuration                │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  EnvoyFilter             │  ALL         │  直接修改任意 xDS 资源             │
│                          │              │  ├── ADD/INSERT_BEFORE/AFTER      │
│                          │              │  ├── REMOVE                       │
│                          │              │  └── MERGE                        │
├──────────────────────────┼──────────────┼────────────────────────────────────┤
│  IstioOperator           │  -           │  不产生 xDS                       │
│                          │              │  生成 K8s resources (Helm 渲染)    │
└──────────────────────────┴──────────────┴────────────────────────────────────┘
```

---

## 九、调试 CRD 与 xDS 的对应关系

```bash
# === 1. 查看 CRD 内容 ===

kubectl get vs reviews-route -n production -o yaml
kubectl get dr reviews-dr -n production -o yaml
kubectl get gw my-gateway -n production -o yaml
kubectl get se external-api -n production -o yaml
kubectl get pa default -n production -o yaml
kubectl get ap backend-authz -n production -o yaml

# === 2. 查看 Envoy 收到的 xDS 配置 ===

# 查看 RDS (VirtualService → Route)
istioctl proxy-config route my-pod -n production -o json

# 查看 CDS (DestinationRule → Cluster)
istioctl proxy-config cluster my-pod -n production -o json

# 查看 LDS (Gateway/Sidecar → Listener)
istioctl proxy-config listener my-pod -n production -o json

# 查看 EDS (Endpoints)
istioctl proxy-config endpoint my-pod -n production -o json

# === 3. 对比 CRD 和 xDS ===

# 例如: 验证 VirtualService 是否正确推送到 Envoy
# 步骤 1: 查看 CRD 中的路由规则
kubectl get vs reviews-route -n production \
  -o jsonpath='{.spec.http[0].route}'

# 步骤 2: 查看 Envoy 中的路由规则
istioctl proxy-config route my-pod -n production --name 8080 -o json | \
  jq '.[].virtualHosts[].routes[]'

# 步骤 3: 确认匹配

# === 4. 验证 EnvoyFilter 是否正确应用 ===

# 查看 Envoy 的完整 config dump
kubectl exec my-pod -c istio-proxy -- \
  curl -s localhost:15000/config_dump | jq '.configs[]' > envoy-config.json

# 搜索 EnvoyFilter 中添加的 filter
cat envoy-config.json | jq '.. | .name? // empty' | grep "custom_filter"

# === 5. 诊断 CRD 未生效的原因 ===

# 检查 istiod 日志中的错误
kubectl logs -n istio-system deploy/istiod | grep -i "error\|warn"

# 检查配置验证状态
istioctl analyze -n production

# 检查 proxy 同步状态
istioctl proxy-status

# 检查 xDS 推送历史
kubectl logs -n istio-system deploy/istiod | grep "Pushing"
```

---

## 十、CRD 之间的依赖关系

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CRD 依赖关系图                                     │
│                                                                      │
│  ┌──────────────┐                                                   │
│  │ServiceEntry  │ (或 K8s Service)                                  │
│  └──────┬───────┘                                                   │
│         │ 定义服务和 endpoint                                         │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────┐    绑定到     ┌──────────┐                        │
│  │VirtualService│ ◀─────────── │ Gateway  │ (外部入口)               │
│  └──────┬───────┘              └──────────┘                        │
│         │ 路由规则指向 subset                                         │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────┐                                                   │
│  │DestinationRule│                                                  │
│  │  ├── subsets  │ ← 依赖 Pod labels                                │
│  │  ├── trafficPolicy                                               │
│  │  └── tls     │                                                   │
│  └──────┬───────┘                                                   │
│         │ subset → Pod selection                                     │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────┐    限制配置范围                                     │
│  │   Sidecar    │ ──────────────▶ Envoy 只看到相关 Service           │
│  └──────────────┘                                                   │
│                                                                      │
│  ┌──────────────┐    mTLS 模式                                      │
│  │    Peer      │ ──────────────▶ Listener TLS 配置                  │
│  │Authentication│                                                  │
│  └──────────────┘                                                   │
│                                                                      │
│  ┌──────────────┐    JWT 验证                                       │
│  │  Request     │ ──────────────▶ JWT Authn HTTP Filter             │
│  │Authentication│                                                  │
│  └──────┬───────┘                                                   │
│         │ 设置 metadata                                              │
│         ▼                                                            │
│  ┌──────────────┐    RBAC                                            │
│  │Authorization │ ──────────────▶ RBAC HTTP Filter                  │
│  │   Policy     │ ← 使用 JWT metadata 和 mTLS identity              │
│  └──────────────┘                                                   │
│                                                                      │
│  ┌──────────────┐    遥测                                            │
│  │  Telemetry   │ ──────────────▶ Stats/Tracing/AccessLog 配置      │
│  └──────────────┘                                                   │
│                                                                      │
│  ┌──────────────┐    Wasm 扩展                                      │
│  │ WasmPlugin   │ ──────────────▶ Wasm HTTP Filter                  │
│  └──────────────┘                                                   │
│                                                                      │
│  ┌──────────────┐    底层补丁 (最后手段)                              │
│  │ EnvoyFilter  │ ──────────────▶ 直接修改任意 xDS 资源              │
│  └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

有具体场景需要深入展开的，随时提问。
