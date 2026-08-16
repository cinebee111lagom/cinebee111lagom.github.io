---
title: 企业 Spring Cloud 微服务在 Kubernetes 上的底层细节
date: 2026-09-07 16:15:00
tags:
  - Spring Cloud
  - Kubernetes
  - 微服务
  - Nacos
categories:
  - Kubernetes
---

### 一、核心架构映射

在传统 Spring Cloud 体系中，许多组件的功能可以与 K8s 原生能力做映射：

| Spring Cloud 组件 | 功能 | K8s 原生替代方案 |
|---|---|---|
| **Eureka / Nacos** | 服务注册与发现 | K8s Service + CoreDNS |
| **Spring Cloud Gateway / Zuul** | API 网关 | K8s Ingress Controller（如 Nginx Ingress、Traefik）或 Gateway API |
| **Spring Cloud Config** | 配置中心 | ConfigMap + Secret，或继续使用 Nacos |
| **Hystrix / Resilience4j** | 熔断限流 | Istio / Linkerd Service Mesh 的熔断策略 |
| **Spring Cloud LoadBalancer** | 客户端负载均衡 | K8s Service 的 kube-proxy / IPVS 负载均衡 |
| **Spring Cloud Bus** | 事件总线 | 可保留（通过 MQ）或用 ConfigMap 热更新 |

> **关键认知**：在 K8s 上，不是"替换一切"，而是根据团队能力和运维需求做**混合架构**决策。很多企业保留 Nacos 作为配置中心（因为其功能远超 ConfigMap），同时使用 K8s Service 做服务发现。

---

### 二、Pod 层面的底层运行细节

#### 2.1 容器启动流程

```
kubectl apply -f deployment.yaml
        │
        ▼
APIServer 接收请求 → etcd 写入期望状态
        │
        ▼
Scheduler 选择 Node → 绑定 Pod 到 Node
        │
        ▼
kubelet watch 到新 Pod → 调用 CRI（containerd）拉镜像
        │
        ▼
containerd 通过 CNI 插件分配 Pod IP
        │
        ▼
启动 Init Containers（如有）→ 按序执行完毕
        │
        ▼
启动主容器 → Spring Boot 应用进程 PID 1
        │
        ▼
Readiness Probe 成功 → Endpoints Controller 将 Pod IP 加入 Service Endpoints
        │
        ▼
流量可达
```

#### 2.2 一个典型 Deployment 的底层状态流转

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 滚动更新时最多多出1个Pod
      maxUnavailable: 0  # 更新过程中不允许不可用
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
        version: v2.1.0
    spec:
      terminationGracePeriodSeconds: 60  # 优雅停机时间
      containers:
      - name: order-service
        image: registry.example.com/order-service:v2.1.0
        ports:
        - containerPort: 8080
        env:
        - name: SPRING_PROFILES_ACTIVE
          value: "k8s,production"
        - name: NACOS_SERVER_ADDR
          valueFrom:
            configMapKeyRef:
              name: common-config
              key: nacos-addr
        - name: JAVA_OPTS
          value: "-Xms512m -Xmx512m -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
        resources:
          requests:
            cpu: "500m"
            memory: "768Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
        readinessProbe:          # 就绪探针：决定是否接收流量
          httpGet:
            path: /actuator/health/readiness
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 5
          failureThreshold: 3
        livenessProbe:           # 存活探针：决定是否重启容器
          httpGet:
            path: /actuator/health/liveness
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 10
          failureThreshold: 5
        lifecycle:
          preStop:               # 优雅停机钩子
            exec:
              command: ["/bin/sh", "-c", "sleep 10"]
```

#### 2.3 滚动更新的底层时序（你真正需要理解的）

```
时间线 ──────────────────────────────────────────────────►

旧Pod-1  [Running]──────────────────[Terminating]──[Deleted]
旧Pod-2  [Running]──────────────────────[Terminating]──[Deleted]
旧Pod-3  [Running]──────────────────────────[Terminating]──[Deleted]
                                   
新Pod-1         [ContainerCreating]──[Running(readiness fail)]──[Running(ready)]
新Pod-2                    [ContainerCreating]──[Running(readiness fail)]──[Running(ready)]
新Pod-3                              [ContainerCreating]──[Running]──[Ready]
```

**关键细节**：
- `preStop` 中的 `sleep 10` 是为了确保**旧 Pod 从 Endpoints 中摘除后再停止接收请求**，避免请求打到正在终止的 Pod
- `terminationGracePeriodSeconds` 必须大于 `preStop` 执行时间 + Spring Boot 关闭时间
- kube-proxy 更新 iptables/IPVS 规则有**几秒延迟**，这就是为什么需要 sleep

---

### 三、网络层面的底层细节

#### 3.1 Service → Endpoints → Pod 的数据链路

```
客户端 Pod
    │
    │ DNS 查询 order-service.production.svc.cluster.local
    ▼
CoreDNS（集群内 DNS）
    │
    │ 返回 ClusterIP（虚拟IP，如 10.96.45.123）
    ▼
iptables / IPVS 规则（由 kube-proxy 维护）
    │
    │ DNAT：ClusterIP → 真实 Pod IP（如 10.244.1.5:8080）
    ▼
CNI 插件（如 Calico/Flannel）封装 → 跨节点路由
    │
    ▼
目标 Pod 接收请求
```

**Spring Cloud 场景的特殊之处**：如果你的服务同时使用了 Spring Cloud LoadBalancer 或 Feign，客户端可能**直接通过 Pod IP 发起请求**（绕过 Service ClusterIP），这会导致：
- Pod 重启后 IP 变化，出现连接失败
- 需要配合 readinessProbe 避免流量打到未就绪的 Pod

#### 3.2 Service Mesh（Istio）下的 sidecar 代理

当企业引入 Istio 时，每个 Pod 会多一个 Envoy sidecar：

```
┌─────────────────────────────────────────────┐
│  Pod: order-service                          │
│  ┌──────────────┐    ┌───────────────────┐  │
│  │ order-service │    │ istio-proxy       │  │
│  │ (Spring Boot) │◄──►│ (Envoy sidecar)   │  │
│  │ port: 8080    │    │ port: 15001/15006 │  │
│  └──────────────┘    └───────────────────┘  │
│                           │                  │
│              iptables REDIRECT 所有流量到 Envoy │
└─────────────────────────────────────────────┘
```

流量路径变为：
```
应用 → localhost:8080 → iptables 拦截 → Envoy(outbound) 
    → 网络 → Envoy(inbound) → iptables → 应用:8080
```

**对 Spring Cloud 的影响**：
- 熔断、重试、负载均衡可以全部交给 Istio，Spring Cloud 层面可以去掉 Resilience4j/LoadBalancer
- 但 **Spring Cloud Gateway 仍然需要**，因为 Envoy 不擅长应用层的复杂路由逻辑

---

### 四、配置管理的底层细节

#### 4.1 ConfigMap 挂载的两种方式

```yaml
# 方式一：环境变量注入（简单，但无法热更新）
env:
- name: NACOS_SERVER_ADDR
  valueFrom:
    configMapKeyRef:
      name: app-config
      key: nacos-addr

# 方式二：Volume 挂载（支持热更新）
volumes:
- name: config-volume
  configMap:
    name: app-config
containers:
- volumeMounts:
  - name: config-volume
    mountPath: /config
```

**ConfigMap 热更新机制的底层**：
- kubelet 通过 watch 监听 ConfigMap 变化
- 变化后更新 Pod 内的挂载文件（本质是符号链接切换）
- **更新延迟约 1-2 分钟**（取决于 kubelet 的 sync 频率）
- Spring Boot 应用需要配合 `spring.cloud.kubernetes.reload.enabled=true` 才能感知变化

#### 4.2 企业常见做法：Nacos + K8s 混合配置

```yaml
# bootstrap.yml (Spring Cloud Kubernetes)
spring:
  application:
    name: order-service
  cloud:
    kubernetes:
      config:
        enabled: true
        sources:
          - name: order-service-config    # 优先级高
            namespace: production
      secrets:
        enabled: true
        sources:
          - name: order-service-secrets
  # Nacos 作为二级配置源
  cloud:
    nacos:
      config:
        server-addr: ${NACOS_SERVER_ADDR}
        namespace: prod
        group: DEFAULT_GROUP
```

**优先级链**：K8s Secret > K8s ConfigMap > Nacos 配置 > 应用内 application.yml

---

### 五、资源管理与 JVM 在容器中的适配

#### 5.1 JVM 感知容器资源限制

JDK 8u191+ 和 JDK 10+ 开始自动感知 cgroup 资源限制，但**仍需要手动调优**：

```yaml
env:
- name: JAVA_OPTS
  value: >-
    -XX:+UseContainerSupport
    -XX:MaxRAMPercentage=75.0
    -XX:InitialRAMPercentage=50.0
    -XX:+UseG1GC
    -XX:MaxGCPauseMillis=200
    -XX:+ExitOnOutOfMemoryError
    -Djava.security.egd=file:/dev/./urandom
```

**关键问题**：如果 `resources.limits.memory` 设为 1Gi，JVM 堆最大约 768MB（75%），剩下的 25% 用于：
- Metaspace（类元数据）
- 线程栈（每线程约 1MB）
- DirectByteBuffer（Netty 等 NIO 框架使用）
- JIT 编译缓存
- GC 开销

**OOMKilled 的常见原因**：堆设太大 → 非堆内存不足 → RSS 超过 limit → kubelet 发 SIGKILL

#### 5.2 资源配额的底层执行机制

```
kubelet → CRI → containerd → runc → Linux cgroup v2
                                        │
                                        ├── cpu.max → CPU 带宽限制
                                        ├── memory.max → 内存硬限制
                                        ├── memory.high → 内存软限制（触发回收）
                                        └── io.max → 磁盘 IO 限制
```

当 Pod 内存使用超过 `limits.memory`：
1. 内核 OOM Killer 被触发
2. 选择该 cgroup 中 RSS 最大的进程（通常是 JVM）
3. 发送 SIGKILL（JVM 无法捕获）
4. kubelet 记录 `OOMKilled` 状态
5. Pod 被重启

---

### 六、可观测性底层架构

```
┌─────────────────────────────────────────────────────┐
│                  可观测性三支柱                        │
│                                                      │
│  Metrics（指标）     Logs（日志）     Traces（链路）    │
│      │                  │                │           │
│  Prometheus          Fluent Bit      Jaeger/         │
│  + Grafana           + ES/Loki       SkyWalking      │
│      │                  │                │           │
│  ServiceMonitor     DaemonSet        Agent注入        │
│  自动发现             节点级采集       Sidecar/JavaAgent│
└─────────────────────────────────────────────────────┘
```

**Spring Boot Actuator + Prometheus 的底层**：

```yaml
# ServiceMonitor (Prometheus Operator)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: order-service
spec:
  selector:
    matchLabels:
      app: order-service
  endpoints:
  - port: management
    path: /actuator/prometheus
    interval: 15s
```

Prometheus 通过 K8s API watch ServiceMonitor CRD → 自动发现 Endpoints → 拉取 `/actuator/prometheus` 指标。

---

### 七、生产环境 Checklist

| 维度 | 关键配置 | 底层原因 |
|---|---|---|
| **优雅停机** | `preStop: sleep 10` + `terminationGracePeriodSeconds: 60` | 等待 Endpoints 更新 + inflight 请求完成 |
| **探针配置** | readiness 用 `/actuator/health`，liveness 用 `/actuator/health/liveness` | 避免 liveness 误杀正在初始化的 Pod |
| **Pod 反亲和** | `podAntiAffinity` 确保副本分散到不同节点 | 单节点故障不会全部宕机 |
| **HPA** | 基于 CPU/内存或自定义指标自动扩缩 | 应对流量波峰波谷 |
| **PDB** | `PodDisruptionBudget: minAvailable: 2` | 维护节点时保证最小可用副本数 |
| **资源限制** | requests ≈ 日常负载，limits ≈ 1.5-2倍 requests | 既保证调度合理，又允许突发 |
| **NetworkPolicy** | 限制 Pod 间通信范围 | 零信任网络，减少攻击面 |

---

以上就是 Spring Cloud 微服务在 K8s 上运行时，你需要关注的**底层技术细节**。如果你有具体的场景想深入讨论（比如某个组件的迁移方案、某个问题的排查思路），随时告诉我。
