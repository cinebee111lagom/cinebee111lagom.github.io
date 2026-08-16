---
title: Istio Profile 底层细节全解析
date: 2026-09-07 14:45:00
tags:
  - Istio
  - Helm
  - Service Mesh
  - Kubernetes
categories:
  - Kubernetes
---

## 一、Profile 的本质 — Helm Values 的预设组合

### 1.1 一个 Profile 就是一份 values.yaml

```
用户执行:
  istioctl install --set profile=default

底层执行:
  helm template istiod manifests/charts/istio-control/istio-discovery \
    -f profiles/default.yaml \
    -f 用户自定义 overlay

本质:
  Profile = 一组预定义的 Helm values
  istioctl install = Helm 渲染模板 + kubectl apply
```



### 1.2 Profile 文件的物理位置

```bash
# Istio 源码中的目录结构
istio/
├── manifests/
│   ├── charts/
│   │   ├── base/                          # CRD + ValidatingWebhook
│   │   │   ├── Chart.yaml
│   │   │   └── templates/
│   │   │       ├── crds.yaml              # 所有 CRD 定义
│   │   │       └── validatingwebhook.yaml
│   │   │
│   │   ├── istio-control/
│   │   │   └── istio-discovery/           # istiod 核心 Chart
│   │   │       ├── Chart.yaml
│   │   │       ├── values.yaml            # 默认 values (最全)
│   │   │       └── templates/
│   │   │           ├── deployment.yaml    # istiod Deployment
│   │   │           ├── service.yaml       # istiod Service
│   │   │           ├── configmap.yaml     # mesh config
│   │   │           ├── serviceaccount.yaml
│   │   │           └── ...
│   │   │
│   │   ├── istio-ingress/                 # Ingress Gateway Chart
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml
│   │   │   └── templates/
│   │   │
│   │   └── istio-egress/                  # Egress Gateway Chart
│   │       ├── Chart.yaml
│   │       ├── values.yaml
│   │       └── templates/
│   │
│   └── profiles/                          # ★ Profile 定义目录
│       ├── default.yaml                   # 默认 profile
│       ├── demo.yaml                      # 演示 profile
│       ├── minimal.yaml                   # 最小 profile
│       ├── empty.yaml                     # 空 profile
│       ├── preview.yaml                   # 预览特性 profile
│       └── external.yaml                  # 外部控制平面
```

---

## 二、六个内置 Profile 的底层对比

### 2.1 default Profile — 生产默认

```yaml
# profiles/default.yaml (简化版，展示关键字段)
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    accessLogFile: /dev/stdout          # 访问日志输出位置
    enableAutoMtls: true                 # 自动 mTLS
    defaultConfig:
      tracing:
        sampling: 1.0                    # 追踪采样率 1%
      holdApplicationUntilProxyStarts: false
      proxyMetadata: {}
      tracing: {}                        # 追踪配置

  components:
    base:                                # CRD 和 Webhook
      enabled: true

    pilot:                               # istiod
      enabled: true
      k8s:
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
        hpaSpec:
          minReplicas: 1
          maxReplicas: 5
          metrics:
            - type: Resource
              resource:
                name: cpu
                targetAverageUtilization: 80
        strategy:
          rollingUpdate:
            maxSurge: 100%
            maxUnavailable: 25%

    ingressGateways:                     # Ingress Gateway
      - name: istio-ingressgateway
        enabled: true
        k8s:
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
          hpaSpec:
            minReplicas: 1
            maxReplicas: 5
          service:
            type: LoadBalancer
            ports:
              - name: http2
                port: 80
                targetPort: 8080
              - name: https
                port: 443
                targetPort: 8443
              - name: tls
                port: 15443
                targetPort: 15443

    egressGateways:                      # Egress Gateway
      - name: istio-egressgateway
        enabled: false                   # ← 默认关闭

  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m                    # Sidecar 默认 CPU 请求
            memory: 128Mi               # Sidecar 默认内存请求
          limits:
            cpu: 2000m
            memory: 256Mi
        logLevel: warning               # Envoy 日志级别
        componentLogLevel: "misc:error"
        concurrency: 2                  # Worker 线程数
        includeIPRanges: ""             # 出站重定向范围
        excludeIPRanges: ""
        excludeInboundPorts: ""
        excludeOutboundPorts: ""

      mtls:                             # 全局 mTLS 配置
        auto: true                      # PERMISSIVE 模式自动升级

      logging:
        level: "default:info"

    pilot:
      autoscaleEnabled: true
      autoscaleMin: 1
      autoscaleMax: 5
      traceSampling: 1.0
      env: {}
      cpu:
        targetAverageUtilization: 80

    telemetry:
      enabled: true
      v2:
        enabled: true
        prometheus:
          enabled: true

    meshConfig:
      defaultConfig:
        holdApplicationUntilProxyStarts: false
```



### 2.2 demo Profile — 适合学习和测试

```yaml
# profiles/demo.yaml (与 default 的差异部分)
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    accessLogFile: /dev/stdout
    enableAutoMtls: true
    defaultConfig:
      tracing:
        sampling: 100.0    # ← 100% 采样 (default 是 1%)

  components:
    pilot:
      enabled: true
      k8s:
        resources:
          requests:
            cpu: 50m       # ← 更低的资源请求 (适合开发环境)
            memory: 128Mi
        hpaSpec:
          minReplicas: 1
          maxReplicas: 1   # ← 固定 1 副本 (不自动扩缩)

    ingressGateways:
      - name: istio-ingressgateway
        enabled: true
        k8s:
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
          hpaSpec:
            minReplicas: 1
            maxReplicas: 1
          service:
            type: ClusterIP  # ← ClusterIP (开发环境不需要 LoadBalancer)

    egressGateways:
      - name: istio-egressgateway
        enabled: true        # ← 开启 (default 是关闭)
        k8s:
          hpaSpec:
            minReplicas: 1
            maxReplicas: 1

  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 50m         # ← Sidecar 更低资源
            memory: 64Mi
        logLevel: debug      # ← debug 日志 (default 是 warning)

    pilot:
      autoscaleEnabled: false
```

### 2.3 minimal Profile — 只有控制平面

```yaml
# profiles/minimal.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    base:
      enabled: true

    pilot:
      enabled: true          # ← 只有 istiod

    ingressGateways: []      # ← 空！没有 Ingress Gateway

    egressGateways: []       # ← 空！没有 Egress Gateway

  values:
    global:
      omitSidecarInjectorConfigMap: true  # ← 不生成 sidecar 注入配置
      proxy:
        resources: {}
```

**底层影响：**

```
安装 minimal profile 后集群中只有:
├── istiod Deployment (1 副本)
├── istiod Service
├── istiod ServiceAccount
├── istio-reader-clusterrole
├── istiod-clusterrole
├── istiod ClusterRoleBinding
├── istio-cni (如果启用)
├── ValidatingWebhookConfiguration
└── CRDs

没有:
├── ❌ istio-ingressgateway
├── ❌ istio-egressgateway
└── ❌ istio-cni (默认)
```

### 2.4 empty Profile — 完全空白

```yaml
# profiles/empty.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec: {}
```

```
所有组件都必须在 --set 或 overlay 中显式启用:
  istioctl install --set profile=empty \
    --set components.pilot.enabled=true \
    --set components.base.enabled=true
```

### 2.5 preview Profile — 预览特性

```yaml
# profiles/preview.yaml
# 基于 default，但启用实验性特性
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"          # ← DNS 代理
        ISTIO_META_DNS_AUTO_ALLOCATE: "true"    # ← 自动分配 DNS

  values:
    pilot:
      env:
        PILOT_ENABLE_STATUS: "true"             # ← IstioStatus API
        # 可能还有其他实验性环境变量

    # Ambient 模式组件 (Istio 1.20+)
    ztunnel:
      enabled: false                            # ← preview 中可能启用
```

### 2.6 external Profile — 外部控制平面

```yaml
# profiles/external.yaml
# 控制平面运行在另一个集群中
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: external     # 自引用

  components:
    base:
      enabled: true     # CRD 仍然需要在数据平面集群中安装

    pilot:
      enabled: false    # ← istiod 不在此集群安装

    ingressGateways:
      - name: istio-ingressgateway
        enabled: true
        k8s:
          env:
            - name: ISTIO_META_REQUESTED_NETWORK_VIEW
              value: "external"

  values:
    global:
      remotePilotAddress: istiod.istio-system.svc:15012
      # ← 指向远端集群的 istiod
      pilotCertProvider: istiod
```

---

## 三、Profile 选择的完整对比矩阵

```
┌───────────────────────┬──────────┬──────┬─────────┬─────────┬──────────┬──────────┐
│  组件/特性             │ default  │ demo │ minimal │ empty   │ preview  │ external │
├───────────────────────┼──────────┼──────┼─────────┼─────────┼──────────┼──────────┤
│  CRDs (base)          │    ✅    │  ✅  │   ✅    │   ❌    │   ✅     │   ✅     │
│  istiod               │    ✅    │  ✅  │   ✅    │   ❌    │   ✅     │   ❌     │
│  Ingress Gateway      │    ✅    │  ✅  │   ❌    │   ❌    │   ✅     │   ✅     │
│  Egress Gateway       │    ❌    │  ✅  │   ❌    │   ❌    │   ❌     │   ❌     │
├───────────────────────┼──────────┼──────┼─────────┼─────────┼──────────┼──────────┤
│  istiod 副本数         │  1-5     │  1   │  1      │   -     │  1-5     │   -      │
│  istiod CPU 请求       │  200m    │  50m │  200m   │   -     │  200m    │   -      │
│  Gateway 副本数        │  1-5     │  1   │  -      │   -     │  1-5     │  1-5     │
│  Sidecar CPU 请求      │  100m    │  50m │  100m   │   -     │  100m    │  100m    │
│  Sidecar 内存请求      │  128Mi   │ 64Mi │  128Mi  │   -     │  128Mi   │  128Mi   │
├───────────────────────┼──────────┼──────┼─────────┼─────────┼──────────┼──────────┤
│  Access Log           │  stdout  │stdout│  -      │   -     │  stdout  │  stdout  │
│  追踪采样率            │  1%      │ 100% │  1%     │   -     │  1%      │  1%      │
│  Envoy 日志级别        │  warning │ debug│  -      │   -     │  warning │  warning │
│  自动 mTLS            │  ✅      │  ✅  │  ✅     │   -     │  ✅      │  ✅      │
│  HPA                  │  ✅      │  ❌  │  ❌     │   -     │  ✅      │  ✅      │
│  Telemetry v2         │  ✅      │  ✅  │  ✅     │   -     │  ✅      │  ✅      │
│  DNS 代理             │  ❌      │  ❌  │  ❌     │   -     │  ✅      │  ❌      │
├───────────────────────┼──────────┼──────┼─────────┼─────────┼──────────┼──────────┤
│  适用场景             │  生产    │ 学习 │ 轻量生产 │ 完全自定义│ 测试新特性│ 多集群   │
│                       │  环境    │ 测试 │         │         │          │          │
└───────────────────────┴──────────┴──────┴─────────┴─────────┴──────────┴──────────┘
```

---

## 四、Profile → Helm Values → K8s Resources 的完整渲染链

### 4.1 istioctl install 的内部执行流程

```
用户执行:
  istioctl install --set profile=demo \
    --set values.pilot.autoscaleMax=3 \
    -f custom-overlay.yaml

    │
    ▼ Step 1: 加载 Profile
    │
    │  读取 profiles/demo.yaml
    │  得到基础 values
    │
    ▼ Step 2: 合并 overlay
    │
    │  merge priority (从低到高):
    │  ├── 1. Helm Chart values.yaml (Chart 默认值)
    │  ├── 2. Profile yaml (demo.yaml)
    │  ├── 3. IstioOperator overlay (--set)
    │  └── 4. IstioOperator overlay (-f custom-overlay.yaml)
    │
    │  合并规则: 深度递归合并 (Deep Merge)
    │  同一字段: 更高优先级覆盖
    │  数组: 替换 (不追加)
    │
    ▼ Step 3: 生成 Manifest
    │
    │  内部调用 Helm 的 render 逻辑:
    │  ├── 渲染 base chart
    │  ├── 渲染 istio-discovery chart
    │  ├── 渲染 istio-ingress chart
    │  └── 渲染 istio-egress chart
    │
    │  每个 Chart 的 templates/ 目录中的模板
    │  接收合并后的 values 作为渲染上下文
    │
    ▼ Step 4: 检测差异 (Dry Run)
    │
    │  将渲染结果与集群中现有资源对比
    │  生成 Diff:
    │  ├── + 新增资源
    │  ├── ~ 变更资源
    │  └── - 删除资源
    │
    ▼ Step 5: 确认 & 应用
    │
    │  显示 Diff 给用户确认
    │  kubectl apply (Server-Side Apply)
    │
    ▼ 完成
```

### 4.2 Helm Template 渲染示例

```yaml
# profiles/demo.yaml 中的相关 values:
spec:
  components:
    pilot:
      k8s:
        hpaSpec:
          minReplicas: 1
          maxReplicas: 1

# manifests/charts/istio-control/istio-discovery/templates/hpa.yaml:
{{- if .Values.pilot.autoscaleEnabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: istiod
  namespace: {{ .Release.Namespace }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: istiod
  minReplicas: {{ .Values.pilot.autoscaleMin }}        # ← 1
  maxReplicas: {{ .Values.pilot.autoscaleMax }}        # ← 1 (demo)
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.pilot.cpu.targetAverageUtilization }}  # ← 80
{{- end }}

# 渲染结果 (demo profile):
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: istiod
  namespace: istio-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: istiod
  minReplicas: 1
  maxReplicas: 1
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 80
```

```yaml
# manifests/charts/istio-control/istio-discovery/templates/deployment.yaml (简化):
apiVersion: apps/v1
kind: Deployment
metadata:
  name: istiod
  namespace: {{ .Release.Namespace }}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: istiod
      istio: pilot
  template:
    metadata:
      labels:
        app: istiod
        istio: pilot
        sidecar.istio.io/inject: "false"    # istiod 自身不注入 sidecar
      annotations:
        sidecar.istio.io/inject: "false"
    spec:
      serviceAccountName: istiod
      containers:
        - name: discovery
          image: "{{ .Values.global.hub }}/pilot:{{ .Values.global.tag }}"
          args:
            - "discovery"
            - "--monitoringAddr=:15014"
            - "--log_output_level=default:{{ .Values.global.logging.level }}"
            - "--domain"
            - "cluster.local"
            - "--keepaliveMaxServerConnectionAge"
            - "30m"
          ports:
            - containerPort: 8080
              name: http-localhost-discovery    # 本地调试
            - containerPort: 15010
              name: grpc-xds                   # xDS 明文
            - containerPort: 15012
              name: grpc-xds-mtls              # xDS mTLS
            - containerPort: 15014
              name: http-monitoring            # Prometheus
            - containerPort: 15017
              name: https-webhook              # Admission Webhook
          resources:
            requests:
              cpu: {{ .Values.pilot.cpu }}m     # demo: 50m
              memory: {{ .Values.pilot.memory }} # demo: 128Mi
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            {{- range $key, $val := .Values.pilot.env }}
            - name: {{ $key }}
              value: "{{ $val }}"
            {{- end }}
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 1
            periodSeconds: 3
            timeoutSeconds: 5
          livenessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 1
            periodSeconds: 3
            timeoutSeconds: 5
          volumeMounts:
            - name: config-volume
              mountPath: /etc/istio/config
            - name: istio-token
              mountPath: /var/run/secrets/tokens
            - name: istiod-ca-cert
              mountPath: /var/run/secrets/istio
      volumes:
        - name: config-volume
          configMap:
            name: istio
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

---

## 五、Profile 合并的深度机制

### 5.1 四层合并顺序

```
Layer 1: Chart defaults (最低优先级)
    │     manifests/charts/*/values.yaml
    │     所有字段的初始默认值
    │
    ▼ 深度合并
Layer 2: Profile (次低优先级)
    │     profiles/<name>.yaml
    │     覆盖 Layer 1 中的同名字段
    │
    ▼ 深度合并
Layer 3: IstioOperator spec.overlay (--set / -f)
    │     用户命令行传入
    │     覆盖 Layer 1 + 2 中的同名字段
    │
    ▼ 深度合并
Layer 4: IstioOperator spec (最高优先级)
          IstioOperator 资源的 spec.components 字段
          直接控制组件级别的开关和配置
```

### 5.2 合并示例

```yaml
# Layer 1: Chart values.yaml
# istio-control/istio-discovery/values.yaml
pilot:
  autoscaleEnabled: true
  autoscaleMin: 1
  autoscaleMax: 5
  traceSampling: 1.0
  resources:
    requests:
      cpu: 200m
      memory: 256Mi

# Layer 2: profiles/demo.yaml
pilot:
  autoscaleEnabled: false        # 覆盖: true → false
  autoscaleMin: 1                # 不变
  autoscaleMax: 1                # 覆盖: 5 → 1
  traceSampling: 100.0           # 覆盖: 1.0 → 100.0

# Layer 3: --set
# istioctl install --set profile=demo --set values.pilot.autoscaleMax=3
pilot:
  autoscaleMax: 3                # 覆盖: 1 → 3

# Layer 4: IstioOperator spec.components
# 也可以通过 IstioOperator CR 覆盖
spec:
  components:
    pilot:
      k8s:
        hpaSpec:
          maxReplicas: 2          # 最终覆盖: 3 → 2

# 最终合并结果:
pilot:
  autoscaleEnabled: false        # 来自 Layer 2
  autoscaleMin: 1                # 来自 Layer 1 (未被覆盖)
  autoscaleMax: 2                # 来自 Layer 4 (最高优先级)
  traceSampling: 100.0           # 来自 Layer 2
  resources:
    requests:
      cpu: 200m                  # 来自 Layer 1 (未被覆盖)
      memory: 256Mi              # 来自 Layer 1 (未被覆盖)
```

### 5.3 数组合并的陷阱

```yaml
# ⚠️ 数组不会合并，而是直接替换

# Layer 1 (Chart defaults):
spec:
  components:
    ingressGateways:
      - name: istio-ingressgateway
        enabled: true
        k8s:
          hpaSpec:
            minReplicas: 1
            maxReplicas: 5

# Layer 2 (Profile overlay):
spec:
  components:
    ingressGateways:
      - name: istio-ingressgateway
        enabled: true
        k8s:
          hpaSpec:
            minReplicas: 1
            maxReplicas: 1    # ← 修改

# 正确理解: 数组整体替换，不是逐元素合并
# 如果 Layer 2 的 ingressGateways 只有一个元素
# Layer 1 中多余的元素会被丢弃

# ❌ 常见错误: 尝试添加第二个 gateway
# 错误理解: 两个 gateway 都会存在
# 实际结果: 只有 overlay 中声明的 gateway 存在
spec:
  components:
    ingressGateways:
      - name: istio-ingressgateway       # ← 替换了 Layer 1 的整个数组
        enabled: true
      - name: my-custom-gateway          # ← 新增
        enabled: true

# ✅ 正确做法: 保留原有 gateway + 添加新的
spec:
  components:
    ingressGateways:
      - name: istio-ingressgateway
        enabled: true
        k8s:
          hpaSpec:
            minReplicas: 1
            maxReplicas: 5
      - name: my-custom-gateway
        enabled: true
        k8s:
          service:
            type: NodePort
```

---

## 六、Profile 中 values 对 Envoy 的影响

### 6.1 从 values 到 Envoy bootstrap

```
Profile values
    │
    ▼
istiod 读取 ConfigMap "istio" (mesh config)
    │
    ▼ 为每个 Pod 生成 Envoy Bootstrap 配置
    │
    │  Bootstrap = Envoy 启动时的初始配置
    │  包含: 与 istiod 的连接信息、Node 元数据、统计配置
    │
    ▼ Bootstrap 被注入到 istio-proxy 容器的 /etc/istio/bootstrap/envoy-rev0.json
    │
    ▼ Envoy 启动时读取 Bootstrap → 连接 istiod → 接收 xDS 推送
```

```json
// Envoy Bootstrap 配置 (由 istiod 根据 values 生成)
{
  "node": {
    "id": "sidecar~10.244.1.15~my-app.production~production.svc.cluster.local",
    "metadata": {
      "NAMESPACE": "production",
      "APP_CONTAINERS": "my-app",
      "ISTIO_PROXY_SHA": "istio-proxy:xxx",
      "ISTIO_VERSION": "1.20.0",
      "POD_NAME": "my-app-6f8b9c4d5-x7k2z",
      "INSTANCE_IP": "10.244.1.15",
      "istio": "sidecar"
    },
    "locality": {
      "region": "us-east-1",
      "zone": "us-east-1a"
    }
  },
  "static_resources": {
    "clusters": [
      {
        "name": "xds-grpc",
        "type": "STRICT_DNS",
        "typed_extension_protocol_options": {
          "envoy.extensions.upstreams.http.v3.HttpProtocolOptions": {
            "@type": "type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions",
            "explicit_http_config": {
              "http2_protocol_options": {}
            }
          }
        },
        "load_assignment": {
          "cluster_name": "xds-grpc",
          "endpoints": [{
            "lb_endpoints": [{
              "endpoint": {
                "address": {
                  "socket_address": {
                    "address": "istiod.istio-system.svc",
                    "port_value": 15012
                  }
                }
              }
            }]
          }]
        },
        "transport_socket": {
          "name": "envoy.transport_sockets.tls",
          "typed_config": {
            "@type": "type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext",
            "common_tls_context": {
              "tls_certificate_sds_secret_configs": [{
                "name": "default",
                "sds_config": {
                  "api_config_source": {
                    "api_type": "GRPC",
                    "grpc_services": [{
                      "envoy_grpc": {
                        "cluster_name": "sds-grpc"
                      }
                    }]
                  }
                }
              }]
            }
          }
        }
      }
    ]
  },
  "dynamic_resources": {
    "lds_config": {
      "ads": {},
      "resource_api_version": "V3"
    },
    "cds_config": {
      "ads": {},
      "resource_api_version": "V3"
    },
    "ads_config": {
      "api_type": "DELTA_GRPC",
      "transport_api_version": "V3",
      "grpc_services": [{
        "envoy_grpc": {
          "cluster_name": "xds-grpc"
        }
      }]
    }
  },
  "overload_manager": {
    "resource_monitors": [{
      "name": "envoy.resource_monitors.global_downstream_max_connections",
      "typed_config": {
        "@type": "type.googleapis.com/envoy.extensions.resource_monitors.downstream_connections.v3.DownstreamConnectionsConfig",
        "max_active_downstream_connections": 2147483647
      }
    }],
    "actions": [{
      "name": "envoy.overload_actions.shrink_heap",
      "triggers": [{
        "name": "envoy.resource_monitors.global_downstream_max_connections",
        "threshold": {
          "value": 0.95
        }
      }]
    }]
  },
  "tracing": {
    "http": {
      "name": "envoy.tracers.zipkin",
      "typed_config": {
        "@type": "type.googleapis.com/envoy.config.trace.v3.ZipkinConfig",
        "collector_cluster": "zipkin",
        "collector_endpoint_version": "HTTP_JSON",
        "collector_endpoint": "/api/v2/spans",
        "shared_span_context": false
      }
    }
  },
  "stats_config": {
    "stats_tags": [
      { "tag_name": "cluster", "regex": "^cluster\\.((.+?)\\.)" },
      { "tag_name": "listener", "regex": "^listener\\.((.+?)\\.)" }
    ],
    "use_all_default_tags": false
  },
  "stats_sinks": [
    {
      "name": "envoy.stat_sinks.metrics_service",
      "typed_config": {
        "@type": "type.googleapis.com/envoy.config.metrics.v3.MetricsServiceConfig",
        "grpc_service": {
          "envoy_grpc": {
            "cluster_name": "xds-grpc"
          }
        }
      }
    }
  ]
}
```

### 6.2 Profile values 对 Envoy bootstrap 的具体映射

```
┌─────────────────────────────────────────┬──────────────────────────────────────────┐
│  Profile values 字段                     │  Envoy Bootstrap 中的对应位置             │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  pilot.traceSampling: 1.0              │  → istiod 中: 按此概率决定是否记录 trace  │
│                                         │  → Envoy Bootstrap: 不直接体现           │
│                                         │    (由 istiod xDS 决定)                   │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.proxy.logLevel: warning        │  → Envoy 启动参数:                        │
│                                         │    --log-level warning                   │
│                                         │  → 或 Bootstrap: runtime override        │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.proxy.concurrency: 2           │  → Envoy 启动参数:                        │
│                                         │    --concurrency 2                       │
│                                         │  → Envoy 创建 2 个 Worker 线程            │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.proxy.resources.requests       │  → K8s Pod spec:                         │
│    cpu: 100m                           │    containers[istio-proxy].resources     │
│    memory: 128Mi                       │    不影响 Envoy 内部配置                   │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.proxy.componentLogLevel        │  → Envoy 启动参数:                        │
│    "misc:error"                        │    --component-log-level misc:error      │
│                                         │  → 控制各组件独立日志级别                   │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.proxy.holdApplication           │  → 注入 sidecar 容器的环境变量:            │
│  UntilProxyStarts: true                │    WAIT_FOR_POD_STARTUP=true             │
│                                         │  → istio-proxy readiness probe 配置      │
│                                         │  → App 容器启动前等待 Envoy 就绪          │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.proxy.includeIPRanges:          │  → istio-init iptables 规则:             │
│    "10.0.0.0/8,172.16.0.0/12"          │    只重定向目标 IP 在这些范围内的流量       │
│                                         │    其余直连                               │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.proxy.excludeIPRanges:          │  → istio-init iptables 规则:             │
│    "10.0.0.1/32"                       │    排除这些 IP 不重定向                    │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.proxy.excludeInboundPorts:      │  → istio-init iptables 规则:             │
│    "3306,5432"                         │    入站这些端口的流量不拦截                 │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  meshConfig.accessLogFile               │  → istiod xDS 推送给 Envoy:              │
│    : "/dev/stdout"                     │    HCM access_log 配置                   │
│                                         │    文件路径或 stdout                       │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  meshConfig.enableAutoMtls: true       │  → istiod xDS 推送给 Envoy:              │
│                                         │    Cluster transport_socket 配置          │
│                                         │    自动为 PERMISSIVE 或 STRICT            │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│  global.tracer.zipkin.address:          │  → Envoy Bootstrap:                      │
│    "zipkin.istio-system:9411"          │    tracing.http 配置                     │
│                                         │    collector_cluster 指向 zipkin         │
└─────────────────────────────────────────┴──────────────────────────────────────────┘
```

---

## 七、istioctl profile list 和 profile dump

### 7.1 查看内置 Profile 列表

```bash
istioctl profile list

# Istio configuration profiles:
#     default
#     demo
#     empty
#     external
#     minimal
#     preview
```

### 7.2 查看 Profile 的完整渲染结果

```bash
# dump 一个 profile 的最终 values (合并后)
istioctl profile dump demo

# 只查看特定路径
istioctl profile dump demo --config-path components.pilot

# 输出:
# components:
#   pilot:
#     enabled: true
#     k8s:
#       env:
#         - name: PILOT_TRACE_SAMPLING
#           value: "100"
#       hpaSpec:
#         maxReplicas: 1
#         minReplicas: 1
#       resources:
#         requests:
#           cpu: 50m
#           memory: 128Mi

# 查看完整 manifest (YAML 格式)
istioctl manifest generate --set profile=demo > demo-manifest.yaml

# 查看特定组件的 manifest
istioctl manifest generate --set profile=demo \
  --set components.pilot.enabled=true \
  --set components.base.enabled=false \
  --set components.ingressGateways[0].enabled=false
```

### 7.3 diff 两个 Profile

```bash
# 比较 default 和 demo 的差异
istioctl profile dump default > /tmp/default.yaml
istioctl profile dump demo > /tmp/demo.yaml
diff /tmp/default.yaml /tmp/demo.yaml

# 输出关键差异:
# < (default)                    > (demo)
# ---
# accessLogFile: /dev/stdout     accessLogFile: /dev/stdout  (相同)
# sampling: 1.0                  sampling: 100.0             (不同)
# autoscaleEnabled: true         autoscaleEnabled: false     (不同)
# autoscaleMax: 5                autoscaleMax: 1             (不同)
# cpu: 200m                      cpu: 50m                    (不同)
# ...
```

---

## 八、自定义 Profile 的创建与使用

### 8.1 创建自定义 Profile 文件

```yaml
# my-production-profile.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: production-profile
spec:
  profile: default                     # 基于 default profile

  meshConfig:
    accessLogFile: /dev/stdout
    accessLogFormat: |
      [%START_TIME%] "%REQ(:METHOD)% %REQ(X-ENVOY-ORIGINAL-PATH?:PATH)% %PROTOCOL%"
      %RESPONSE_CODE% %RESPONSE_FLAGS% %BYTES_RECEIVED% %BYTES_SENT%
      %DURATION% %RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%
      "%REQ(X-FORWARDED-FOR)%" "%REQ(USER-AGENT)%"
      "%REQ(X-REQUEST-ID)%" "%REQ(:AUTHORITY)%"
      "%UPSTREAM_HOST%" %UPSTREAM_CLUSTER%
    enableAutoMtls: true
    outboundTrafficPolicy:
      mode: REGISTRY_ONLY               # 只允许访问注册的服务
    defaultConfig:
      tracing:
        sampling: 5.0                   # 5% 采样率
      holdApplicationUntilProxyStarts: true
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
      concurrency: 4                    # 4 个 Worker 线程

  components:
    pilot:
      enabled: true
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: "2"
            memory: 2Gi
        hpaSpec:
          minReplicas: 3                # 最少 3 副本 (HA)
          maxReplicas: 10
          metrics:
            - type: Resource
              resource:
                name: cpu
                targetAverageUtilization: 70
            - type: Resource
              resource:
                name: memory
                targetAverageUtilization: 80
        strategy:
          rollingUpdate:
            maxSurge: "100%"
            maxUnavailable: "25%"
        env:
          - name: PILOT_ENABLE_CROSS_CLUSTER_WORKLOAD_ENTRY
            value: "true"
          - name: PILOT_TRACE_SAMPLING
            value: "5"
        podDisruptionBudget:
          minAvailable: 2               # PDB: 至少 2 个可用

    ingressGateways:
      - name: istio-ingressgateway
        enabled: true
        k8s:
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: "2"
              memory: 1Gi
          hpaSpec:
            minReplicas: 3
            maxReplicas: 10
          service:
            type: LoadBalancer
            ports:
              - name: http2
                port: 80
                targetPort: 8080
              - name: https
                port: 443
                targetPort: 8443
              - name: tls
                port: 15443
                targetPort: 15443
          podDisruptionBudget:
            minAvailable: 2

    egressGateways:
      - name: istio-egressgateway
        enabled: true
        k8s:
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
          hpaSpec:
            minReplicas: 2
            maxReplicas: 5

  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: "2"
            memory: 1Gi
        logLevel: warning
        componentLogLevel: "misc:error"
        concurrency: 4
      tracer:
        zipkin:
          address: zipkin.observability.svc:9411

    pilot:
      autoscaleEnabled: true
      autoscaleMin: 3
      autoscaleMax: 10
      cpu:
        targetAverageUtilization: 70

    telemetry:
      enabled: true
      v2:
        enabled: true
        prometheus:
          enabled: true
        accessLogPolicy:
          enabled: true
```

### 8.2 使用自定义 Profile

```bash
# 方法 1: 直接使用文件作为 IstioOperator
kubectl apply -f my-production-profile.yaml -n istio-system

# 方法 2: istioctl install
istioctl install -f my-production-profile.yaml

# 方法 3: 将自定义 profile 放入 istio 源码的 profiles/ 目录
# 重新编译 istioctl (不推荐)

# 验证安装
istioctl verify-install -f my-production-profile.yaml
```

### 8.3 检查当前安装使用的 Profile

```bash
# 查看当前 IstioOperator
kubectl get iop -n istio-system -o yaml

# 查看当前使用的 profile
istioctl profile dump

# 查看实际运行的配置
kubectl get configmap istio -n istio-system -o yaml

# 查看 istiod 的实际参数
kubectl get deployment istiod -n istio-system -o jsonpath='{.spec.template.spec.containers[0].args}'
```

---

## 九、Profile 的运行时修改

### 9.1 In-Place 升级 Profile

```bash
# 从 minimal 切换到 default
istioctl install --set profile=default

# istioctl 会:
# 1. 加载新的 profile
# 2. 与现有资源 diff
# 3. 显示变更
# 4. 应用 (创建 Ingress Gateway、更新 istiod 配置等)
```

### 9.2 修改单个 values 而不换 Profile

```bash
# 增大 istiod 的采样率
istioctl install --set values.pilot.traceSampling=10.0

# 添加环境变量
istioctl install \
  --set values.pilot.env.PILOT_ENABLE_CROSS_CLUSTER_WORKLOAD_ENTRY=true

# 修改 sidecar 资源限制
istioctl install \
  --set values.global.proxy.resources.requests.cpu=300m \
  --set values.global.proxy.resources.requests.memory=512Mi
```

### 9.3 K8s 层面验证 Profile 变更效果

```bash
# 验证 istiod Deployment 参数
kubectl get deploy istiod -n istio-system -o yaml | \
  grep -A5 "resources:"

# 验证 HPA
kubectl get hpa -n istio-system

# 验证 Ingress Gateway
kubectl get deploy istio-ingressgateway -n istio-system

# 验证 mesh config
kubectl get configmap istio -n istio-system -o jsonpath='{.data.mesh}' | \
  grep accessLogFile

# 验证注入的 sidecar 参数
kubectl get pod my-app -n production -o jsonpath='{.spec.containers[?(@.name=="istio-proxy")].args}'

# 验证注入的 sidecar 资源
kubectl get pod my-app -n production -o jsonpath='{.spec.containers[?(@.name=="istio-proxy")].resources}'
```

---

## 十、Profile 与多集群/多网络的关系

```
┌──────────────────────────────────────────────────────────────────┐
│  多集群部署模式与 Profile 对应关系                                  │
│                                                                   │
│  模式 1: 共享控制平面 (Shared Control Plane)                       │
│  ├── 主集群: istioctl install --set profile=default               │
│  └── 远端集群: istioctl install --set profile=remote              │
│      (remote 已在 1.18 中移除, 推荐用 external)                    │
│                                                                   │
│  模式 2: 外部控制平面 (External Control Plane)                     │
│  ├── 控制平面集群: istioctl install --set profile=default          │
│  └── 数据平面集群: istioctl install -f external-operator.yaml     │
│      profile=external                                             │
│      只安装 CRD + Ingress Gateway + 远端 istiod 配置               │
│                                                                   │
│  模式 3: 主-从 (Primary-Remote)                                   │
│  ├── 主集群: istioctl install --set profile=default               │
│  └── 从集群: istioctl install --set profile=external              │
│      --set values.global.remotePilotAddress=<主集群istiod地址>     │
│                                                                   │
│  模式 4: 多主 (Multi-Primary)                                     │
│  └── 每个集群: istioctl install --set profile=default              │
│      每个集群都有独立的 istiod                                      │
│      通过共享 Root CA 建立信任                                      │
│                                                                   │
│  模式 5: Ambient Mesh                                             │
│  └── istioctl install --set profile=ambient                       │
│      (Istio 1.22+, 使用 ztunnel + waypoint proxy)                 │
└──────────────────────────────────────────────────────────────────┘
```

```yaml
# external profile 的 IstioOperator (数据平面集群)
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: external-istiocontrolplane
spec:
  profile: external

  values:
    global:
      remotePilotAddress: 203.0.113.10       # 主集群 istiod 的外部 IP
      # 或
      # remotePilotAddress: istiod.istio-system.svc.external:15012
      pilotCertProvider: istiod
      configCluster: true                     # 标记这是配置集群

  components:
    base:
      enabled: true                           # CRD 仍然需要

    pilot:
      enabled: false                          # 不安装 istiod

    ingressGateways:
      - name: istio-ingressgateway
        enabled: true
        k8s:
          env:
            - name: ISTIO_META_REQUESTED_NETWORK_VIEW
              value: "network1"               # 网络标识
```

---

## 总结

```
Profile 的本质:

  Profile → Helm Values 预设
           → 控制组件开关 (istiod / gateway)
           → 控制组件规格 (CPU / Memory / 副本数)
           → 控制 Envoy 行为 (日志/采样/并发/拦截范围)
           → 控制网格特性 (mTLS/追踪/访问日志/出站策略)

选择指南:

  开发/学习:  demo (低资源，全特性，debug 日志)
  轻量生产:   minimal (只有 istiod，按需添加 gateway)
  标准生产:   default (推荐，合理资源，默认安全)
  高可用生产:  default + 自定义 overlay (3+ 副本，PDB，高资源)
  测试新特性:  preview (启用实验性功能)
  多集群:     default + external (主集群 + 远端数据面)

核心理解:

  istioctl install = Helm 渲染 + kubectl apply
  Profile          = Helm values 的命名预设
  --set / -f       = 对 Profile 的增量覆盖
  最终产物         = K8s Resources (Deployment/Service/ConfigMap/CRD)
```

有具体场景需要深入展开的，随时提问。
