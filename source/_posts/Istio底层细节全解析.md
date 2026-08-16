---
title: Istio 底层细节全解析
date: 2026-09-07 14:00:00
tags:
  - Istio
  - Envoy
  - Service Mesh
  - Kubernetes
categories:
  - Kubernetes
---

## 一、Istio 架构全景

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Istio 架构总览                                    │
│                                                                          │
│  ┌───────────────────── 控制平面 (Control Plane) ────────────────────┐   │
│  │                                                                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐  │   │
│  │  │  istiod      │  │  istiod      │  │  istiod                 │  │   │
│  │  │              │  │              │  │                         │  │   │
│  │  │  Pilot       │  │  Citadel     │  │  Galley                 │  │   │
│  │  │  (流量管理)   │  │  (证书签发)   │  │  (配置验证/分发)         │  │   │
│  │  │              │  │              │  │                         │  │   │
│  │  │  xDS Server  │  │  CA Server   │  │  Config Validation      │  │   │
│  │  │  (gRPC)      │  │  (Secret     │  │  Webhook                │  │   │
│  │  │              │  │   Discovery) │  │                         │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └────────────┬────────────┘  │   │
│  │         │                 │                        │               │   │
│  └─────────┼─────────────────┼────────────────────────┼───────────────┘   │
│            │                 │                        │                    │
│            │    gRPC Stream  │   SDS (证书)            │  K8s API          │
│            │    (LDS/RDS/    │   (Secret Discovery     │  (CRD Watch)      │
│            │     CDS/EDS)    │    Service)             │                    │
│            │                 │                        │                    │
│  ┌─────────┼─────────────────┼────────────────────────┼───────────────┐   │
│  │         ▼                 ▼                        ▼               │   │
│  │  ┌────────────────────────────────────────────────────────────┐   │   │
│  │  │                    数据平面 (Data Plane)                    │   │   │
│  │  │                                                             │   │   │
│  │  │  ┌───────── Pod A ──────────────────────────────────────┐   │   │   │
│  │  │  │  ┌──────────┐          ┌───────────────────────┐     │   │   │   │
│  │  │  │  │ App 容器  │◀────────▶│  Envoy Sidecar        │     │   │   │   │
│  │  │  │  │          │ localhost │  (istio-proxy)        │     │   │   │   │
│  │  │  │  │          │ :8080     │  ┌─────────────────┐  │     │   │   │   │
│  │  │  │  └──────────┘          │  │ Listener        │  │     │   │   │   │
│  │  │  │                        │  │ Filter Chain    │  │     │   │   │   │
│  │  │  │                        │  │ Cluster         │  │     │   │   │   │
│  │  │  │                        │  │ Route           │  │     │   │   │   │
│  │  │  │                        │  └─────────────────┘  │     │   │   │   │
│  │  │  │                        │  ┌─────────────────┐  │     │   │   │   │
│  │  │  │                        │  │ BPF / iptables  │  │     │   │   │   │
│  │  │  │                        │  │ 流量拦截        │  │     │   │   │   │
│  │  │  │                        │  └─────────────────┘  │     │   │   │   │
│  │  │  └─────────────────────────────────────────────────┘     │   │   │
│  │  │                                                             │   │   │
│  │  └────────────────────────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```



---

## 二、istiod — 单体进程的三大核心模块

### 2.1 进程内部结构

```
┌─────────────────── istiod (单进程) ──────────────────────────┐
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Pilot 模块 (流量管理)                                    │ │
│  │                                                          │ │
│  │  ┌─────────────────┐    ┌──────────────────────────┐    │ │
│  │  │ Config Controller│    │ Service Controller       │    │ │
│  │  │                  │    │                          │    │ │
│  │  │ Watch K8s:       │    │ Watch K8s:               │    │ │
│  │  │ - VirtualService │    │ - Service                │    │ │
│  │  │ - DestinationRule│    │ - Endpoints              │    │ │
│  │  │ - Gateway        │    │ - Pod                    │    │ │
│  │  │ - ServiceEntry   │    │ - Node                   │    │ │
│  │  │ - Sidecar        │    │                          │    │ │
│  │  └────────┬─────────┘    └──────────┬───────────────┘    │ │
│  │           │                         │                    │ │
│  │           ▼                         ▼                    │ │
│  │  ┌─────────────────────────────────────────────────┐    │ │
│  │  │          Internal Push Context                   │    │ │
│  │  │                                                  │    │ │
│  │  │  PushContext 是 Istio 的核心数据结构:              │    │ │
│  │  │  - 全局 Service → Endpoint 映射                   │    │ │
│  │  │  - 全局 VirtualService 路由表                     │    │ │
│  │  │  - 全局 DestinationRule 配置                     │    │ │
│  │  │  - Gateway 绑定信息                              │    │ │
│  │  │  - Sidecar Scope 隔离                            │    │ │
│  │  │                                                  │    │ │
│  │  │  每次配置变更 → 构建新 PushContext → 推送到所有代理  │    │ │
│  │  └────────────────────────┬─────────────────────────┘    │ │
│  │                           │                              │ │
│  │                           ▼                              │ │
│  │  ┌─────────────────────────────────────────────────┐    │ │
│  │  │          xDS Generator                          │    │ │
│  │  │                                                  │    │ │
│  │  │  为每个连接的 Envoy 生成个性化 xDS 响应:          │    │ │
│  │  │  ├── LDS: Listener (按 Service 端口 + 协议)      │    │ │
│  │  │  ├── RDS: Route (按 VirtualService)              │    │ │
│  │  │  ├── CDS: Cluster (按 DestinationRule + Service) │    │ │
│  │  │  ├── EDS: Endpoint (按 Pod IP + 健康状态)        │    │ │
│  │  │  └── NDS: Name Table (DNS 代理配置)              │    │ │
│  │  └─────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Citadel 模块 (安全)                                     │ │
│  │                                                          │ │
│  │  ┌─────────────────────────────────────────────────┐    │ │
│  │  │          Certificate Authority (CA)              │    │ │
│  │  │                                                  │    │ │
│  │  │  Root CA: 从 K8s Secret 或外部 CA 加载            │    │ │
│  │  │  ├── self-signed (默认)                          │    │ │
│  │  │  ├── K8s CSR API (kubernetes.io/legacy-unknown)  │    │ │
│  │  │  └── 外部 CA (HashiCorp Vault, AWS PCA, ...)     │    │ │
│  │  │                                                  │    │ │
│  │  │  为每个 workload 签发 SVID (SPIFFE ID):          │    │ │
│  │  │  spiffe://<trust-domain>/ns/<namespace>/sa/<sa>  │    │ │
│  │  │                                                  │    │ │
│  │  │  证书轮换: 默认 24h, 可配置                       │    │ │
│  │  │  SDS (Secret Discovery Service) 推送新证书        │    │ │
│  │  └─────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Galley 模块 (配置验证)                                   │ │
│  │                                                          │ │
│  │  ┌─────────────────────────────────────────────────┐    │ │
│  │  │          Validating Webhook                      │    │ │
│  │  │                                                  │    │ │
│  │  │  kubectl apply -f virtualservice.yaml            │    │ │
│  │  │  → API Server → Webhook → Galley 验证           │    │ │
│  │  │    ├── schema 验证 (字段类型/必填)                 │    │ │
│  │  │    ├── semantic 验证 (引用的 Service 是否存在)     │    │ │
│  │  │    └── conflict 检测 (路由规则冲突)                │    │ │
│  │  │    → 合法 → 写入 etcd                            │    │ │
│  │  │    → 非法 → 拒绝 (admission denied)              │    │ │
│  │  └─────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```



---

## 三、xDS 协议 — 控制平面与数据平面的通信协议

### 3.1 xDS 全称与各自职责

```
xDS = x Discovery Service

┌──────────┬──────────────────────┬──────────────────────────────────┐
│ 缩写     │ 全称                  │ 推送内容                          │
├──────────┼──────────────────────┼──────────────────────────────────┤
│ LDS      │ Listener Discovery   │ 端口监听配置                      │
│          │ Service              │ Filter Chain 定义                 │
│          │                      │ TLS 上下文                        │
├──────────┼──────────────────────┼──────────────────────────────────┤
│ RDS      │ Route Discovery      │ HTTP 路由规则                     │
│          │ Service              │ VirtualHost → Route 匹配          │
│          │                      │ 权重路由 / 金丝雀 / A-B测试       │
├──────────┼──────────────────────┼──────────────────────────────────┤
│ CDS      │ Cluster Discovery    │ 上游集群定义                      │
│          │ Service              │ 负载均衡策略                      │
│          │                      │ 熔断 / 健康检查 / 连接池          │
├──────────┼──────────────────────┼──────────────────────────────────┤
│ EDS      │ Endpoint Discovery   │ 后端实例列表                      │
│          │ Service              │ Pod IP + Port + 健康状态          │
│          │                      │ 权重 / Locality                   │
├──────────┼──────────────────────┼──────────────────────────────────┤
│ SDS      │ Secret Discovery     │ TLS 证书                          │
│          │ Service              │ mTLS 私钥                         │
│          │                      │ CA 证书链                         │
├──────────┼──────────────────────┼──────────────────────────────────┤
│ ADS      │ Aggregated Discovery │ 聚合所有 xDS 到单一 gRPC stream   │
│          │ Service              │ 保证推送顺序一致性                  │
├──────────┼──────────────────────┼──────────────────────────────────┤
│ NDS      │ Name Discovery       │ DNS 代理配置                      │
│          │ Service              │ Istio 的 auto-allocate DNS        │
├──────────┼──────────────────────┼──────────────────────────────────┤
│ ECDS     │ Extension Config     │ Filter 的动态配置更新              │
│          │ Discovery Service    │ 不重建 Listener 就能更新 filter    │
└──────────┴──────────────────────┴──────────────────────────────────┘
```

### 3.2 ADS gRPC 通信协议

```
Envoy (Client)                         istiod (Server)
     │                                      │
     │──── gRPC Stream 建立 ──────────────▶│
     │     POST /envoy.service.discovery.v3│
     │          .AggregatedDiscoveryService│
     │          /StreamAggregatedResources │
     │                                      │
     │──── DiscoveryRequest (LDS) ────────▶│
     │     {                                │
     │       version_info: "",              │
     │       node: {                        │
     │         id: "sidecar~10.244.1.15~   │
     │              my-app~production",     │
     │         metadata: {                  │
     │           NAMESPACE: "production",   │
     │           APP_CONTAINERS: "my-app",  │
     │           ISTIO_VERSION: "1.20.0"    │
     │         }                            │
     │       },                             │
     │       type_url: "...Listener",       │
     │       resource_names: []             │
     │     }                                │
     │                                      │
     │◀─── DiscoveryResponse (LDS) ────────│
     │     {                                │
     │       version_info: "v1",            │
     │       resources: [                   │
     │         Listener { ... },            │
     │         Listener { ... }             │
     │       ],                             │
     │       type_url: "...Listener"        │
     │     }                                │
     │                                      │
     │──── ACK (LDS) ─────────────────────▶│
     │     {                                │
     │       version_info: "v1",            │
     │       type_url: "...Listener",       │
     │       response_nonce: "abc123"       │
     │     }                                │
     │                                      │
     │──── DiscoveryRequest (RDS) ────────▶│
     │     ... (同理)                        │
     │                                      │
     │──── DiscoveryRequest (CDS) ────────▶│
     │     ... (同理)                        │
     │                                      │
     │──── DiscoveryRequest (EDS) ────────▶│
     │     ... (同理)                        │
     │                                      │
     │     (持续保持 gRPC stream 打开)       │
     │     (istiod 有变更时主动 Push)        │
     │                                      │
```

### 3.3 Push 机制 — 增量与全量

```go
// istiod 中的 Push 流程 (pilot/pkg/xds/ads.go 简化)

// 1. 配置变更触发 Push
func (s *DiscoveryServer) HandleRequest() {
    // K8s Watch 检测到 Service/Endpoints/VirtualService 变更
    // 或 Pod 增删
    // → 创建 PushRequest
    pushReq := &PushRequest{
        Full: true,                    // 全量推送
        ConfigsUpdated: map[ConfigKey]struct{}{
            {Kind: "ServiceEntry", Name: "my-app"}: {},
        },
    }
    // 投递到全局 push channel
    s.pushChannel <- pushReq
}

// 2. PushContext 重建 (全量时)
func (s *DiscoveryServer) InitPushContext() {
    // 构建新的 PushContext
    // 遍历所有 Service → 建立索引
    // 遍历所有 VirtualService → 建立路由树
    // 遍历所有 DestinationRule → 建立策略映射
    // 遍历所有 Sidecar → 建立可见性范围
    newPushContext := model.NewPushContext()
    newPushContext.InitContext(env, oldPushContext, pushReq.ConfigsUpdated)
}

// 3. 为每个连接的 Envoy 生成响应
func (s *DiscoveryServer) pushToClient(con *Connection, pushReq *PushRequest) {
    // 根据 Node 元数据确定该代理需要哪些资源
    // 例如: sidecar 类型的代理只需要与它相关的 Service

    // 生成 LDS
    listeners := s.ConfigGenerator.BuildListeners(con, pushContext)
    con.sendLDS(listeners, pushContext.Version)

    // 生成 CDS
    clusters := s.ConfigGenerator.BuildClusters(con, pushContext)
    con.sendCDS(clusters, pushContext.Version)

    // 生成 RDS (依赖 Listener 中的 route_config_name)
    routes := s.ConfigGenerator.BuildHTTPRoutes(con, pushContext)
    con.sendRDS(routes, pushContext.Version)

    // 生成 EDS (依赖 Cluster 中的 eds_cluster_name)
    endpoints := s.ConfigGenerator.BuildEndpoints(con, pushContext)
    con.sendEDS(endpoints, pushContext.Version)
}
```

### 3.4 增量推送 (Delta xDS)

```
Istio 1.12+ 支持增量 xDS:

全量推送 (SotW - State of the World):
  ├── 每次推送所有资源
  ├── Envoy 需要对比差异
  └── 大规模集群: 推送数据量大，延迟高

增量推送 (Delta):
  ├── 只推送变更的资源
  ├── remove: 删除的资源列表
  ├── resources: 新增/更新的资源列表
  └── 大规模集群: 推送数据量小，延迟低

示例: 一个 Pod 删除时
  Delta EDS:
  {
    system_version_info: "v5",
    resources: [],          // 无新增
    removed_resources: [
      "outbound|80||my-app.default.svc.cluster.local"
      // → 实际上只移除一个 endpoint
    ]
  }
```

---

## 四、Sidecar 注入 — 从 Webhook 到运行的完整流程

### 4.1 Mutating Admission Webhook

```
kubectl apply -f deployment.yaml
    │
    ▼
API Server 收到请求
    │
    ▼ Admission Controller 链
    │
    ├── MutatingWebhookConfiguration (istio-sidecar-injector)
    │   │
    │   │  webhook 配置:
    │   │  {
    │   │    "webhooks": [{
    │   │      "name": "sidecar-injector.istio.io",
    │   │      "clientConfig": {
    │   │        "service": {
    │   │          "name": "istiod",
    │   │          "namespace": "istio-system",
    │   │          "path": "/inject"
    │   │        }
    │   │      },
    │   │      "namespaceSelector": {
    │   │        "matchLabels": {
    │   │          "istio-injection": "enabled"
    │   │        }
    │   │      },
    │   │      "rules": [{
    │   │        "operations": ["CREATE"],
    │   │        "apiGroups": [""],
    │   │        "apiVersions": ["v1"],
    │   │        "resources": ["pods"]
    │   │      }]
    │   │    }]
    │   │  }
    │   │
    │   ▼ API Server 调用 istiod 的 /inject 端点
    │
    ▼ istiod 处理注入请求
    │
    │  1. 读取 Pod spec 和 namespace labels
    │
    │  2. 检查注入条件:
    │     ├── namespace 有 istio-injection=enabled?
    │     ├── Pod annotation: sidecar.istio.io/inject != "false"?
    │     ├── 不是 Job without completion?
    │     └── 不是已注入的 Pod?
    │
    │  3. 生成 Patch (JSON Patch):
    │     ├── 添加 init 容器 (istio-init)
    │     ├── 添加 sidecar 容器 (istio-proxy)
    │     ├── 修改 volume mounts
    │     ├── 添加 service account token volume
    │     └── 注入 annotation 元数据
    │
    │  4. 返回 JSON Patch 给 API Server
    │
    ▼ API Server 应用 Patch → 创建修改后的 Pod
```

### 4.2 注入的具体内容

```yaml
# 原始 Pod spec (用户提交的)
spec:
  containers:
    - name: my-app
      image: my-app:v1
      ports:
        - containerPort: 8080

# 注入后的 Pod spec (API Server 实际创建的)
spec:
  # ===== 新增: Init 容器 =====
  initContainers:
    - name: istio-init
      image: docker.io/istio/proxyv2:1.20.0
      command:
        - istio-iptables
        - -p                    # Envoy 入站端口
        - "15001"
        - -z                    # 所有入站流量重定向目标端口
        - "15006"
        - -u                    # 排除的 UID (envoy 用户)
        - "1337"
        - -m                    # 重定向模式: REDIRECT
        - REDIRECT
        - -i                    # 排除的 IP 范围
        - "*"                   # 重定向所有出站流量
        - -b                    # 入站端口
        - "8080"                # 只拦截应用端口
        - -d                    # 不拦截的入站端口
        - "15090,15021,15020"   # Envoy 自身端口
      securityContext:
        capabilities:
          add:
            - NET_ADMIN         # 需要修改 iptables 的权限
            - NET_RAW
        runAsUser: 0            # root 用户
      restartPolicy: Always

  containers:
    - name: my-app
      image: my-app:v1
      ports:
        - containerPort: 8080

    # ===== 新增: Sidecar 容器 =====
    - name: istio-proxy
      image: docker.io/istio/proxyv2:1.20.0
      args:
        - proxy
        - sidecar
        - --domain
        - $(POD_NAMESPACE).svc.cluster.local
        - --proxyLogLevel=warning
        - --proxyComponentLogLevel=misc:error
        - --log_output_level=default:info
        - --serviceCluster
        - my-app.$(POD_NAMESPACE)
        - --drainDuration
        - 45s
        - --parentShutdownDuration
        - 60s
        - --discoveryAddress
        - istiod.istio-system.svc:15012
        - --proxyAdminPort
        - "15000"               # Envoy Admin API 端口
        - --statusPort
        - "15020"               # 就绪探针端口
        - --controlPlaneAuthPolicy
        - MUTUAL_TLS            # 与 istiod 的 mTLS 通信
        - --trust-domain
        - cluster.local
        - --concurrency
        - "2"                   # Worker 线程数
      ports:
        - containerPort: 15090  # Prometheus metrics
          name: http-envoy-prom
        - containerPort: 15020  # 健康检查
          name: http-health
      env:
        - name: INSTANCE_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
      readinessProbe:
        httpGet:
          path: /healthz/ready
          port: 15020
        initialDelaySeconds: 1
        periodSeconds: 2
      securityContext:
        runAsUser: 1337         # envoy 用户 (不与 root 冲突)
        runAsGroup: 1337

  # ===== 新增: Volumes =====
  volumes:
    - name: istio-envoy
      emptyDir:
        medium: Memory          # tmpfs，Envoy 共享内存
    - name: istio-data
      emptyDir: {}
    - name: istio-podinfo
      downwardAPI:
        items:
          - path: labels
            fieldRef:
              fieldPath: metadata.labels
          - path: annotations
            fieldRef:
              fieldPath: metadata.annotations
    - name: istio-token
      projected:
        sources:
          - serviceAccountToken:
              path: istio-token
              expirationSeconds: 43200
              audience: istio-ca
    - name: istiod-ca-cert
      configMap:
        name: istio-ca-root-cert
```

### 4.3 istio-init 容器的 iptables 脚本详解

```bash
#!/bin/bash
# istio-iptables 的完整执行流程

# ========== 环境变量 ==========
PROXY_PORT=15001          # Envoy 出站监听端口
INBOUND_CAPTURE_PORT=15006 # Envoy 入站监听端口
PROXY_UID=1337            # Envoy 进程的 UID
PROXY_GID=1337            # Envoy 进程的 GID
INBOUND_PORTS_INCLUDE="8080"   # 需要拦截的入站端口
INBOUND_PORTS_EXCLUDE="15090,15020,15021"  # 排除的端口
OUTBOUND_IP_RANGES_INCLUDE="*" # 重定向所有出站
OUTBOUND_PORTS_EXCLUDE=""      # 排除的出站端口
KUBEVIRT_INTERFACES=""         # KubeVirt 特殊接口

# ========== 清除旧规则 ==========
iptables -t nat -F
iptables -t mangle -F
iptables -F
iptables -X

# ========== 创建自定义链 ==========
iptables -t nat -N ISTIO_INBOUND
iptables -t nat -N ISTIO_IN_REDIRECT
iptables -t nat -N ISTIO_OUTPUT
iptables -t nat -N ISTIO_REDIRECT

# ========== 应用程序流量 (UID != PROXY_UID) ==========

# OUTPUT 链: 所有出站流量进入 ISTIO_OUTPUT
iptables -t nat -A OUTPUT -p tcp -j ISTIO_OUTPUT

# ISTIO_OUTPUT: 排除 Envoy 自身的流量 (防死循环)
iptables -t nat -A ISTIO_OUTPUT -m owner --uid-owner ${PROXY_UID} -j RETURN
iptables -t nat -A ISTIO_OUTPUT -m owner --gid-owner ${PROXY_GID} -j RETURN

# ISTIO_OUTPUT: 排除目标是 localhost 的流量
iptables -t nat -A ISTIO_OUTPUT -d 127.0.0.1/32 -j RETURN

# ISTIO_OUTPUT: 重定向其他出站到 Envoy 出站端口
iptables -t nat -A ISTIO_OUTPUT -j ISTIO_REDIRECT
iptables -t nat -A ISTIO_REDIRECT -p tcp -j REDIRECT --to-port ${PROXY_PORT}

# ========== 入站流量 ==========

# PREROUTING 链: 入站流量进入 ISTIO_INBOUND
iptables -t nat -A PREROUTING -p tcp -j ISTIO_INBOUND

# ISTIO_INBOUND: 只拦截指定端口
iptables -t nat -A ISTIO_INBOUND -p tcp --dport 8080 -j ISTIO_IN_REDIRECT
# 排除探针端口
iptables -t nat -A ISTIO_INBOUND -p tcp --dport 15090 -j RETURN
iptables -t nat -A ISTIO_INBOUND -p tcp --dport 15020 -j RETURN

# ISTIO_IN_REDIRECT: 重定向到 Envoy 入站端口
iptables -t nat -A ISTIO_IN_REDIRECT -p tcp -j REDIRECT --to-port ${INBOUND_CAPTURE_PORT}

# ========== mangle 表 (连接标记) ==========
# 标记入站连接 (用于 Envoy 识别)
iptables -t mangle -A PREROUTING -p tcp -j TPROXY \
  --on-port ${INBOUND_CAPTURE_PORT} --tproxy-mark 0x111/0x111
```

---

## 五、证书与 mTLS — 底层安全机制

### 5.1 SPIFFE 身份模型

```
每个工作负载的唯一身份:

SPIFFE ID 格式:
  spiffe://<trust-domain>/<workload-identifier>

示例:
  spiffe://cluster.local/ns/production/sa/my-app-sa
  ├── trust-domain: cluster.local
  ├── namespace: production
  └── service-account: my-app-sa

X.509 SVID (SPIFFE Verifiable Identity Document):
  证书的 SAN (Subject Alternative Name) 字段:
  URI: spiffe://cluster.local/ns/production/sa/my-app-sa

  证书结构:
  ├── Issuer: istiod.istio-system.svc.cluster.local
  ├── Subject: (空, 不使用 CN)
  ├── SAN:
  │   ├── URI: spiffe://cluster.local/ns/production/sa/my-app-sa
  │   └── DNS: my-app.production.svc.cluster.local
  ├── Not Before: 2024-01-01 00:00:00
  ├── Not After:  2024-01-02 00:00:00  (24h 有效期)
  ├── Key Usage: Digital Signature, Key Encipherment
  ├── Ext Key Usage: Server Auth, Client Auth
  └── Signature Algorithm: SHA256-RSA
```

### 5.2 证书签发流程

```
Pod 启动
    │
    ▼
istio-proxy (Envoy) 进程启动
    │
    ▼ SDS Client 连接 istiod (gRPC, mTLS)
    │
    │──── SDS Request ────────────────────────▶│
    │     {                                    │
    │       resource_names: ["ROOTCA"],        │
    │       node: { ... }                      │
    │     }                                    │
    │                                          │
    │◀─── SDS Response (Root CA) ─────────────│
    │     {                                    │
    │       ca_certificate: {                  │
    │         inline_bytes: "-----BEGIN CERT..."│
    │       }                                  │
    │     }                                    │
    │                                          │
    │──── SDS Request ────────────────────────▶│
    │     {                                    │
    │       resource_names: ["default"],       │
    │       // 请求 workload 证书               │
    │     }                                    │
    │                                          │
    │     istiod CA 签发证书:                    │
    │     ├── 1. 读取 Pod 的 ServiceAccount    │
    │     ├── 2. 构建 SPIFFE ID               │
    │     │   spiffe://cluster.local/ns/       │
    │     │   production/sa/my-app-sa          │
    │     ├── 3. 生成 CSR (Certificate Sign    │
    │     │   Request)                         │
    │     ├── 4. CA 签名                       │
    │     │   root key → 签发 workload cert    │
    │     └── 5. 设置有效期 (24h)              │
    │                                          │
    │◀─── SDS Response (Workload Cert) ───────│
    │     {                                    │
    │       certificate_chain: {               │
    │         inline_bytes: "-----BEGIN CERT..."│
    │       },                                 │
    │       private_key: {                     │
    │         inline_bytes: "-----BEGIN RSA..."│
    │       }                                  │
    │     }                                    │
    │                                          │
    │  (24h 后自动轮换，Envoy 重新请求)          │
    │                                          │
    │◀─── SDS Push (新证书) ─────────────────│
    │     (istiod 主动推送轮换后的新证书)         │
```

### 5.3 mTLS 握手的内核层面

```
┌───────────── Envoy A ────────────┐          ┌──────────── Envoy B ────────────┐
│                                   │          │                                  │
│  App 代码:                         │          │  App 代码:                        │
│  HTTP GET /api/users              │          │  listen(8080)                    │
│       │                           │          │       │                           │
│  localhost:15001                  │          │  Envoy 入站 15006                 │
│  (Envoy outbound)                │          │  (Envoy inbound)                 │
│       │                           │          │       │                           │
│  Envoy 出站处理:                    │          │  Envoy 入站处理:                   │
│  ├── 查路由表 → Cluster           │          │                                  │
│  ├── 查 Endpoint → Pod B IP      │          │                                  │
│  └── 需要 mTLS? (PERMISSIVE/STRICT)         │                                  │
│       │                           │          │                                  │
│       ▼                           │          │                                  │
│  TLS 握手开始:                      │          │                                  │
│       │                           │          │                                  │
│  ┌────┴──────────────────────────────────────┴────┐                             │
│  │                                                │                             │
│  │  ClientHello (Envoy A)                         │                             │
│  │  ├── TLS 1.3                                   │                             │
│  │  ├── Cipher Suites: TLS_AES_256_GCM_SHA384    │                             │
│  │  ├── ALPN: istio, istio-h2                     │                             │
│  │  ├── SNI: (可选, 用于路由)                       │                             │
│  │  └── (TLS 1.3: 包含 key_share)                 │                             │
│  │                                                │                             │
│  │  ServerHello + EncryptedExtensions (Envoy B)   │                             │
│  │  ├── Certificate: X.509 SVID                   │                             │
│  │  │   SAN: spiffe://cluster.local/              │                             │
│  │  │         ns/production/sa/my-app-sa          │                             │
│  │  ├── CertificateVerify (签名)                   │                             │
│  │  └── Finished                                  │                             │
│  │                                                │                             │
│  │  Client Certificate (Envoy A)                  │                             │
│  │  ├── Certificate: X.509 SVID                   │                             │
│  │  │   SAN: spiffe://cluster.local/              │                             │
│  │  │         ns/production/sa/caller-sa          │                             │
│  │  └── CertificateVerify + Finished              │                             │
│  │                                                │                             │
│  │  TLS 握手完成                                   │                             │
│  │  ALPN 协商: istio-h2 → 使用 HTTP/2 codec       │                             │
│  │                                                │                             │
│  └────────────────────────────────────────────────┘                             │
│       │                           │          │                                  │
│  加密的 HTTP/2 流量               │          │  解密后:                           │
│  经过物理网络传输                  │          │  ├── RBAC 检查源 identity          │
│                                  │          │  ├── 提取 SPIFFE ID               │
│                                  │          │  └── 转发到 App:8080               │
└──────────────────────────────────┘          └──────────────────────────────────┘
```

### 5.4 mTLS 模式

```yaml
# PeerAuthentication CRD
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT      # 只接受 mTLS 连接
    # mode: PERMISSIVE # 同时接受 mTLS 和明文 (迁移期间使用)
    # mode: DISABLE    # 禁用 mTLS (不推荐)
```

```
STRICT 模式下的流量拒绝:

客户端 (无 sidecar) ──plaintext──▶ Envoy 入站端口 15006
                                      │
                                      ▼
                                 TLS Inspector 检测
                                 发现非 TLS 流量
                                      │
                                      ▼
                                 Filter Chain 匹配失败
                                 (只配置了 tls transport_protocol 的 chain)
                                      │
                                      ▼
                                 连接被关闭
                                 RST_STREAM / connection reset
```

---

## 六、流量管理 — VirtualService / DestinationRule 的底层实现

### 6.1 VirtualService 如何变成 Envoy Route

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app-route
  namespace: production
spec:
  hosts:
    - my-app.production.svc.cluster.local
  http:
    - match:
        - headers:
            x-canary:
              exact: "true"
      route:
        - destination:
            host: my-app.production.svc.cluster.local
            subset: canary
          weight: 100

    - match:
        - uri:
            prefix: /api/v2
      route:
        - destination:
            host: my-app.production.svc.cluster.local
            subset: stable
          weight: 90
        - destination:
            host: my-app.production.svc.cluster.local
            subset: canary
          weight: 10
      timeout: 5s
      retries:
        attempts: 3
        perTryTimeout: 2s
        retryOn: "5xx,reset,connect-failure"

    - route:
        - destination:
            host: my-app.production.svc.cluster.local
            subset: stable
          weight: 100
```

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: my-app-dr
  namespace: production
spec:
  host: my-app.production.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30ms
      http:
        h2UpgradePolicy: DEFAULT
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        maxRetries: 3
    loadBalancer:
      simple: LEAST_REQUEST
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
    - name: stable
      labels:
        version: v1
    - name: canary
      labels:
        version: v2
```

### 6.2 Istiod 将 CRD 转换为 xDS 的过程

```
VirtualService + DestinationRule
    │
    ▼ Istiod 内部转换
    │
    │  RDS (RouteConfiguration) 生成:
    │  {
    │    "name": "8080",
    │    "virtualHosts": [{
    │      "name": "my-app.production.svc.cluster.local:8080",
    │      "domains": [
    │        "my-app.production.svc.cluster.local",
    │        "my-app.production.svc",
    │        "my-app.production",
    │        "my-app",
    │        "10.97.42.15:8080"     // ClusterIP
    │      ],
    │      "routes": [
    │        // 路由 1: canary header
    │        {
    │          "match": {
    │            "headers": [{
    │              "name": "x-canary",
    │              "exactMatch": "true"
    │            }]
    │          },
    │          "route": {
    │            "cluster": "outbound|8080|canary|my-app.production.svc.cluster.local",
    │            "timeout": "0s"
    │          }
    │        },
    │        // 路由 2: /api/v2 前缀
    │        {
    │          "match": {
    │            "prefix": "/api/v2"
    │          },
    │          "route": {
    │            "weightedClusters": {
    │              "clusters": [
    │                {
    │                  "name": "outbound|8080|stable|my-app.production.svc.cluster.local",
    │                  "weight": 90
    │                },
    │                {
    │                  "name": "outbound|8080|canary|my-app.production.svc.cluster.local",
    │                  "weight": 10
    │                }
    │              ]
    │            },
    │            "timeout": "5s",
    │            "retryPolicy": {
    │              "retryOn": "5xx,reset,connect-failure",
    │              "numRetries": 3,
    │              "perTryTimeout": "2s"
    │            }
    │          }
    │        },
    │        // 路由 3: 默认
    │        {
    │          "match": {"prefix": "/"},
    │          "route": {
    │            "cluster": "outbound|8080|stable|my-app.production.svc.cluster.local"
    │          }
    │        }
    │      ]
    │    }]
    │  }
    │
    │  CDS (Cluster) 生成:
    │  [
    │    {
    │      "name": "outbound|8080|stable|my-app.production.svc.cluster.local",
    │      "type": "EDS",
    │      "edsClusterConfig": {
    │        "serviceName": "outbound|8080|stable|my-app.production.svc.cluster.local"
    │      },
    │      "lbPolicy": "LEAST_REQUEST",      // ← DestinationRule.loadBalancer
    │      "circuitBreakers": {               // ← DestinationRule.connectionPool
    │        "thresholds": [{
    │          "maxConnections": 100,
    │          "maxPendingRequests": 100,
    │          "maxRequests": 1000
    │        }]
    │      },
    │      "outlierDetection": {              // ← DestinationRule.outlierDetection
    │        "consecutive5xx": 5,
    │        "interval": "10s",
    │        "baseEjectionTime": "30s",
    │        "maxEjectionPercent": 50
    │      },
    │      "transportSocket": {               // ← mTLS 配置
    │        "name": "envoy.transport_sockets.tls",
    │        "typedConfig": {
    │          "commonTlsContext": {
    │            "tlsCertificateSdsSecretConfigs": [{
    │              "name": "default",
    │              "sdsConfig": { ... }
    │            }],
    │            "validationContextSdsSecretConfig": {
    │              "name": "ROOTCA"
    │            },
    │            "alpnProtocols": ["istio", "istio-h2"]
    │          }
    │        }
    │      }
    │    },
    │    {
    │      "name": "outbound|8080|canary|my-app.production.svc.cluster.local",
    │      ...
    │    }
    │  ]
    │
    │  EDS (Endpoint) 生成:
    │  {
    │    "clusterName": "outbound|8080|stable|my-app.production.svc.cluster.local",
    │    "endpoints": [{
    │      "locality": {
    │        "region": "us-east-1",
    │        "zone": "us-east-1a"
    │      },
    │      "lbEndpoints": [
    │        {
    │          "endpoint": {
    │            "address": {
    │              "socketAddress": {
    │                "address": "10.244.1.15",
    │                "portValue": 8080
    │              }
    │            }
    │          },
    │          "metadata": {
    │            "filterMetadata": {
    │              "envoy.lb": {
    │                "version": "v1"  // subset label
    │              }
    │            }
    │          }
    │        },
    │        {
    │          "endpoint": {
    │            "address": {
    │              "socketAddress": {
    │                "address": "10.244.2.20",
    │                "portValue": 8080
    │              }
    │            }
    │          }
    │        }
    │      ]
    │    }]
    │  }
```

---

## 七、Envoy 内部架构 — 单进程内的完整数据流

### 7.1 Envoy 的线程模型

```
┌──────────────────── Envoy 进程 ──────────────────────────┐
│                                                           │
│  ┌──────────────────── 主线程 ──────────────────────────┐ │
│  │  - 信号处理                                          │ │
│  │  - Admin API (localhost:15000)                       │ │
│  │  - xDS 客户端 (gRPC 连接到 istiod)                   │ │
│  │  - Listener 管理 (add/remove/drain)                  │ │
│  │  - 热重启协调                                         │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌──────────────── Worker 线程 0 ──────────────────────┐ │
│  │  - Event Loop (libevent)                             │ │
│  │  - 处理分配给线程 0 的连接                             │ │
│  │  - Filter Chain 执行                                 │ │
│  │  - 统计数据收集                                       │ │
│  │  ┌──────────────────────────────────────────────┐   │ │
│  │  │  Listener Socket 0.0.0.0:15001 (出站)        │   │ │
│  │  │  Listener Socket 0.0.0.0:15006 (入站)        │   │ │
│  │  │  ├── accept() 新连接                          │   │ │
│  │  │  ├── TLS 握手                                 │   │ │
│  │  │  ├── Filter Chain 匹配                        │   │ │
│  │  │  ├── HTTP Codec 解析                          │   │ │
│  │  │  ├── Route 匹配                               │   │ │
│  │  │  ├── 上游连接 (connect to Pod)                │   │ │
│  │  │  └── 数据转发                                 │   │ │
│  │  └──────────────────────────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌──────────────── Worker 线程 1 ──────────────────────┐ │
│  │  (同上，处理另一批连接)                                │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
│  (Worker 线程数 = --concurrency 参数，默认 = CPU 核数)     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 7.2 连接分配机制

```
新连接到达 Listener Socket (0.0.0.0:15001)
    │
    ▼ 内核 accept 队列
    │
    ▼ Envoy 使用 SO_REUSEPORT
    │  多个 Worker 线程监听同一个 socket
    │  内核自动分发连接到不同线程
    │  (避免惊群效应)
    │
    │  setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt))
    │  内核: 使用 hash(saddr, sport, daddr, dport) 选择线程
    │
    ▼ Worker 线程的 Event Loop 收到可读事件
    │
    │  Connection 创建:
    │  ├── 分配 connection buffer
    │  ├── 注册 read/write callback
    │  ├── 创建 Filter Chain 实例
    │  └── 开始处理
```

### 7.3 单个请求的完整执行路径

```
请求: curl http://my-app:80/api/users (从 Pod A 到 Pod B)

=== Pod A 的 Envoy (outbound) ===

1. App → localhost:15001
   │
2. iptables REDIRECT → Envoy 收到连接
   │  getsockopt(SO_ORIGINAL_DST) → 10.97.42.15:80
   │
3. HTTP/1.1 Codec 解析请求:
   │  GET /api/users HTTP/1.1
   │  Host: my-app
   │
4. Route 匹配:
   │  VirtualHost: my-app.production.svc.cluster.local
   │  → Route: prefix "/" → Cluster "outbound|8080||my-app..."
   │
5. Cluster 选择 Endpoint:
   │  LEAST_REQUEST 负载均衡
   │  → 10.244.2.20:8080 (Pod B)
   │
6. 上游连接:
   │  ├── 连接池查找: 是否有到 10.244.2.20:8080 的空闲连接?
   │  ├── 无 → 创建新连接
   │  │   └── mTLS 握手 (如果 STRICT)
   │  └── 有 → 复用
   │
7. 发送请求到上游:
   │  如果 mTLS:
   │  ├── TLS 加密
   │  ├── ALPN: istio-h2
   │  └── HTTP/2 HEADERS frame 发送
   │
8. 等待响应


=== 物理网络传输 ===

   10.244.1.x → 10.244.2.x
   CNI 路由 (Calico BGP / Flannel VXLAN)
   TLS 加密的 TCP 数据包


=== Pod B 的 Envoy (inbound) ===

9.  Pod B 的 eth0 收到数据包
    │
10. iptables TPROXY/REDIRECT → Envoy inbound 15006
    │
11. TLS Inspector:
    │  检测到 TLS → transport_protocol = "tls"
    │  ALPN = "istio-h2" → 选择 HTTP/2 HCM filter chain
    │
12. TLS 解密:
    │  使用 Pod B 的 workload 私钥解密
    │  验证 Pod A 的 workload 证书
    │  提取 SPIFFE ID: spiffe://cluster.local/ns/production/sa/caller-sa
    │
13. HTTP/2 Codec 解析:
    │  HEADERS frame → :method=GET, :path=/api/users
    │
14. RBAC 检查:
    │  源身份: spiffe://cluster.local/ns/production/sa/caller-sa
    │  目标路径: /api/users
    │  → ALLOW (匹配授权策略)
    │
15. 统计记录:
    │  istio_requests_total{source="caller-sa",destination="my-app-sa",
    │    request_operation="GET",response_code="200"} += 1
    │
16. 转发到 App:
    │  连接 127.0.0.1:8080 (localhost → App 容器)
    │  发送 plaintext HTTP/1.1 请求
    │
17. App 处理请求，返回响应
    │
18. 响应原路返回:
    │  App → Envoy inbound (加密) → 物理网络 → Envoy outbound (解密) → App
```

---

## 八、Envoy Admin API — 运行时调试

### 8.1 Admin 端口 15000 的完整端点

```bash
# 进入 sidecar 容器
kubectl exec -it my-pod -c istio-proxy -- /bin/bash

# === 配置类 ===

# 完整配置 dump (非常大)
curl -s localhost:15000/config_dump | jq .

# 只看 Listener
curl -s localhost:15000/config_dump?resource=dynamic_listeners | jq .

# 只看 Cluster
curl -s localhost:15000/config_dump?resource=dynamic_active_clusters | jq .

# 只看 Route
curl -s localhost:15000/config_dump?resource=dynamic_route_configs | jq .

# 只看 Endpoint
curl -s localhost:15000/config_dump?resource=dynamic_endpoint_configs | jq .

# === 运行时状态 ===

# 所有 Listener 概要
curl -s localhost:15000/listeners

# 所有 Cluster 状态
curl -s localhost:15000/clusters

# 所有 Route
curl -s localhost:15000/routes

# 所有 Endpoint
curl -s localhost:15000/endpoints

# 服务端信息
curl -s localhost:15000/server_info | jq .

# 热重启信息
curl -s localhost:15000/hot_restart_version

# === 统计类 ===

# 所有统计 (非常多)
curl -s localhost:15000/stats

# Prometheus 格式指标
curl -s localhost:15000/stats/prometheus

# 只看 HTTP 统计
curl -s localhost:15000/stats?filter=http

# 只看 Cluster 统计
curl -s localhost:15000/stats?filter=cluster

# === 日志类 ===

# 修改日志级别
curl -s -XPOST localhost:15000/logging?level=debug

# 恢复默认
curl -s -XPOST localhost:15000/logging?level=info

# === 操作类 ===

# Drain 所有连接 (优雅关闭)
curl -s -XPOST localhost:15000/drain_listeners

# Drain 特定 Listener
curl -s -XPOST localhost:15000/drain_listeners?inboundonly

# 重置统计
curl -s -XPOST localhost:15000/reset_counters

# 健康检查
curl -s localhost:15000/ready
curl -s localhost:15000/healthz/ready
```

### 8.2 生产环境调试实例

```bash
# === 场景 1: 请求路由到了错误的后端 ===

# 查看路由匹配结果
kubectl exec my-pod -c istio-proxy -- \
  curl -s localhost:15000/config_dump?resource=dynamic_route_configs | \
  jq '.configs[0].dynamicRouteConfigs[0].routeConfig.virtualHosts[] |
    select(.name | contains("my-app")) |
    .routes[] |
    {match: .match, cluster: .route.cluster}'

# === 场景 2: 确认 mTLS 是否生效 ===

# 查看 Cluster 的 TLS 配置
kubectl exec my-pod -c istio-proxy -- \
  curl -s localhost:15000/config_dump?resource=dynamic_active_clusters | \
  jq '.configs[].dynamicActiveClusters[].cluster |
    select(.name | contains("my-app")) |
    .transport_socket'

# 有 transport_socket 且 name = "envoy.transport_sockets.tls" → mTLS 已启用

# === 场景 3: Endpoint 健康状态 ===

kubectl exec my-pod -c istio-proxy -- \
  curl -s localhost:15000/clusters | \
  grep "my-app.*::health_flags"

# healthy / unhealthy / /draining / timeout / degraded

# === 场景 4: 连接池状态 ===

kubectl exec my-pod -c istio-proxy -- \
  curl -s localhost:15000/clusters | \
  grep "my-app.*::cx_active"

# cx_active: 当前活跃连接数
# cx_connect_fail: 连接失败次数
# rq_active: 当前活跃请求
# rq_timeout: 超时请求
# rq_retry: 重试请求
```

---

## 九、istioctl — 深度分析工具

### 9.1 `istioctl analyze` — 配置分析

```bash
# 分析整个集群的配置问题
istioctl analyze -A

# 输出示例:
# Warning [IST0101] (VirtualService my-vs) Referenced host
#   not found in the mesh
# Warning [IST0132] (DestinationRule my-dr) Traffic policy
#   with connection pool limits is configured but no outlier
#   detection is set
# Error   [IST0109] (Gateway my-gw) Referenced gateway port
#   is not defined in any service
```

### 9.2 `istioctl proxy-status` — 代理同步状态

```bash
istioctl proxy-status

# NAME                       CLUSTER      CDS        LDS        EDS        RDS
# my-app-6f8b9c4d5-x7k2z    Kubernetes   SYNCED     SYNCED     SYNCED     SYNCED
# my-app-6f8b9c4d5-abc12     Kubernetes   SYNCED     SYNCED     SYNCED     STALE
#                                                              ↑
#                                         EDS STALE 表示该代理的 Endpoint
#                                         与 istiod 不同步
#                                         可能原因: 网络问题 / 代理卡住

# 对比两个代理的配置
istioctl proxy-status my-app-6f8b9c4d5-x7k2z
```

### 9.3 `istioctl x describe` — 请求路径分析

```bash
# 分析一个 Pod 会如何路由到目标 Service
istioctl x describe pod my-pod

# 输出:
# Pod: my-pod.production
# Ports: 8080/TCP
#
# Destination: my-app.production.svc.cluster.local
# VirtualService: my-app-route (production)
#   Route[0]: header x-canary=true → subset:canary (100%)
#   Route[1]: prefix /api/v2 → subset:stable (90%), subset:canary (10%)
#   Route[2]: default → subset:stable (100%)
#
# DestinationRule: my-app-dr (production)
#   Load Balancer: LEAST_REQUEST
#   Circuit Breaker: maxConnections=100
#   Outlier Detection: consecutive5xx=5, interval=10s
#
# mTLS Mode: STRICT
```

---

## 十、Istio 的内部通信端口一览

```
┌──────────────┬──────────┬────────────────────────────────────┐
│  组件         │  端口     │  用途                               │
├──────────────┼──────────┼────────────────────────────────────┤
│  istiod      │  15010   │  xDS 服务 (明文 gRPC)               │
│              │  15012   │  xDS 服务 (mTLS gRPC) ← 主要端口     │
│              │  15014   │  istiod metrics (Prometheus)       │
│              │  15017   │  Admission Webhook (HTTPS)         │
│              │  8080    │  istiod 调试端口                     │
├──────────────┼──────────┼────────────────────────────────────┤
│  Envoy       │  15000   │  Admin API (localhost only)        │
│  (Sidecar)   │  15001   │  出站流量拦截 (virtual outbound)    │
│              │  15006   │  入站流量拦截 (virtual inbound)     │
│              │  15004   │  Envoy Prometheus metrics          │
│              │  15008   │  HBONE proxy (Ambient 模式)         │
│              │  15020   │  健康检查                           │
│              │  15021   │  健康检查 (只读)                     │
│              │  15090   │  Envoy 统计出口 (Prometheus)        │
├──────────────┼──────────┼────────────────────────────────────┤
│  Ingress GW  │  80/443  │  外部流量入口                       │
│              │  15021   │  健康检查                           │
│              │  15443   │  mTLS passthrough                  │
│              │  15012   │  xDS 连接到 istiod                  │
├──────────────┼──────────┼────────────────────────────────────┤
│  CNI 插件    │  (无)     │  由 kubelet 调用的二进制文件         │
│  (Ambient)   │          │  配置 eBPF / iptables 规则          │
└──────────────┴──────────┴────────────────────────────────────┘
```

---

## 总结：Istio 的数据面与控制面交互时间线

```
时间轴 ──────────────────────────────────────────────────────────────▶

t=0s    K8s 创建 Pod (kubelet)
t=0.1s  API Server 调用 istiod /inject webhook
t=0.2s  istiod 返回 JSON Patch (注入 istio-init + istio-proxy)
t=0.3s  kubelet 拉取镜像
t=0.5s  istio-init 容器执行: iptables 规则配置
t=0.6s  istio-init 完成退出 (exit 0)
t=0.7s  istio-proxy (Envoy) 容器启动
t=0.8s  Envoy 加载 bootstrap 配置
t=0.9s  Envoy 连接 istiod:15012 (gRPC ADS)
t=1.0s  Envoy 发送 Node 信息 (proxy type, metadata, IP)
t=1.1s  istiod 识别到新 proxy
t=1.2s  istiod 推送 LDS: 为该 Pod 的每个端口生成 Listener
t=1.3s  Envoy ACK LDS
t=1.4s  istiod 推送 CDS: 上游 Cluster (所有相关 Service)
t=1.5s  Envoy ACK CDS
t=1.6s  istiod 推送 RDS: 路由规则 (VirtualService)
t=1.7s  Envoy ACK RDS
t=1.8s  istiod 推送 EDS: 后端 Endpoint 列表
t=1.9s  Envoy ACK EDS
t=2.0s  istiod 推送 SDS: Root CA 证书 + Workload 证书
t=2.1s  Envoy 收到证书，完成 mTLS 配置
t=2.2s  Envoy readiness probe /healthz/ready → 200 OK
t=2.3s  kubelet 标记 istio-proxy 就绪
t=2.4s  App 容器开始启动 (如果 readiness probe 配置正确)
t=2.5s  App 就绪 → Pod Ready → Service Endpoints 更新
t=2.6s  istiod 检测到 Endpoints 变更 → 推送 EDS 给所有相关 proxy
t=3.0s  所有 proxy 同步完成，流量可以路由到新 Pod

24h后   SDS 证书即将过期 → istiod 推送新证书 → 无缝轮换

──────────────────────────────────────────────────────────────────────
配置变更时间线:

t=0s    kubectl apply -f new-virtualservice.yaml
t=0.1s  API Server → istiod Watch 检测到变更
t=0.2s  istiod 重建 PushContext
t=0.3s  istiod 构建受影响 proxy 列表
t=0.4s  istiod 推送 RDS (新路由)
t=0.5s  所有受影响的 Envoy 收到新路由 → ACK
t=0.6s  新路由生效

从用户执行 kubectl apply 到流量按新路由转发:
总延迟 < 1 秒 (正常情况)
```

有具体场景需要深入展开的，随时提问。
