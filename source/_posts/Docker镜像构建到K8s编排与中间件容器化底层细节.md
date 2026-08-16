---
title: Docker 镜像构建到 K8s 编排与中间件容器化底层细节
date: 2026-09-07 18:00:00
tags:
  - Docker
  - Kubernetes
  - 镜像构建
  - 中间件
categories:
  - Kubernetes
---

## 一、Docker 镜像构建细节

### 1. 分层构建策略

Docker 镜像的核心是 **分层缓存**。一个 Spring Boot 应用的 Dockerfile 如果写不好，每次改一行代码就要重新下载几百 MB 的依赖，构建极慢。

**推荐写法：利用分层缓存**

```dockerfile
# ========== 第一阶段：构建 ==========
FROM maven:3.9-eclipse-temurin-21 AS builder

WORKDIR /build
# 先只拷贝 pom，利用 Docker 缓存层下载依赖
COPY pom.xml .
RUN mvn dependency:go-offline -B

# 再拷贝源码编译
COPY src ./src
RUN mvn package -DskipTests -B

# ========== 第二阶段：运行 ==========
FROM eclipse-temurin:21-jre-alpine

# 安全：非 root 用户运行
RUN addgroup -S app && adduser -S app -G app

WORKDIR /app

# 只拷贝产物
COPY --from=builder /build/target/*.jar app.jar

# JVM 参数通过环境变量注入
ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:InitialRAMPercentage=50.0 \
               -Djava.security.egd=file:/dev/./urandom"

EXPOSE 8080

USER app
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

**关键点解析：**

| 技术细节 | 说明 |
|---------|------|
| `--from=builder` | 多阶段构建，最终镜像不含 Maven、源码，体积从 ~800MB 缩小到 ~200MB |
| `-XX:+UseContainerSupport` | JDK 10+ 自动识别容器 cgroup 内存/CPU 限制 |
| `MaxRAMPercentage=75.0` | 按容器内存限制的百分比分配堆，避免 OOMKilled |
| `/dev/./urandom` | 加速 JVM 启动时的熵源获取，避免阻塞 |
| 非 root 用户 | 安全最佳实践，防止容器逃逸提权 |

### 2. Spring Boot 分层 Jar 的利用

Spring Boot 2.3+ 支持分层 jar，可以进一步优化缓存：

```xml
<!-- pom.xml -->
<plugin>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-maven-plugin</artifactId>
    <configuration>
        <layers>
            <enabled>true</enabled>
        </layers>
    </configuration>
</plugin>
```

```dockerfile
# 使用 Spring Boot 的分层工具拆分 jar
FROM eclipse-temurin:21-jre-alpine AS builder
WORKDIR /application
COPY target/*.jar app.jar
RUN java -Djarmode=layertools -jar app.jar extract

FROM eclipse-temurin:21-jre-alpine
WORKDIR /application
# 按依赖变化频率从低到高依次拷贝，最大化缓存命中
COPY --from=builder /application/dependencies/ ./
COPY --from=builder /application/spring-boot-loader/ ./
COPY --from=builder /application/snapshot-dependencies/ ./
COPY --from=builder /application/application/ ./
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
```

**分层结构：**
```
┌──────────────────────────┐  ← 变化最频繁（每次改代码）
│    application/          │     业务代码
├──────────────────────────┤  ← 偶尔变化
│  snapshot-dependencies/  │     SNAPSHOT 依赖
├──────────────────────────┤  ← 较少变化
│  spring-boot-loader/     │     Spring Boot 加载器
├──────────────────────────┤  ← 几乎不变
│    dependencies/         │     正式版本依赖
└──────────────────────────┘
```

这样改代码后重新构建，只有最上面一层变化，镜像推送只传输差异层，速度极快。

### 3. JVM 在容器中的内存布局

这是很多人踩坑的地方：

```
容器内存限制 = 512MB
┌─────────────────────────────────────┐
│  Heap（堆）       ≈ 384MB (75%)     │  ← -XX:MaxRAMPercentage=75
│  ┌──────────────┐                   │
│  │ Young Gen    │                   │
│  │ Old Gen      │                   │
│  └──────────────┘                   │
│  Metaspace       ≈ 64MB             │  ← 类元数据
│  Thread Stacks   ≈ 32MB (200线程)   │  ← 每线程 256KB-1MB
│  CodeCache       ≈ 24MB             │  ← JIT 编译产物
│  Direct Memory   ≈ 变量             │  ← NIO/Netty 堆外内存
│  其他开销         ≈ 剩余             │
└─────────────────────────────────────┘
```

**常见 OOMKilled 原因：** 堆设太大，Metaspace + Stack + Direct + 堆 > 容器限制。

```yaml
# K8s 中正确设置
resources:
  requests:
    memory: "512Mi"    # 调度保证
    cpu: "250m"
  limits:
    memory: "512Mi"    # 硬限制，超出就 OOMKilled
    cpu: "1000m"       # 可突发到 1 核
```

---

## 二、K8s 编排部署细节

### 1. 一个完整微服务的 Deployment 定义

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: microservice
  labels:
    app: order-service
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1          # 滚动更新时最多多 1 个 Pod
      maxUnavailable: 0    # 更新期间不允许不可用
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
        version: v1
      annotations:
        prometheus.io/scrape: "true"   # Prometheus 采集标记
        prometheus.io/port: "8080"
    spec:
      terminationGracePeriodSeconds: 60  # 优雅停机等待时间
      
      # 从私有仓库拉取镜像
      imagePullSecrets:
        - name: registry-secret
      
      containers:
        - name: order-service
          image: registry.example.com/micro/order-service:1.2.0
          imagePullPolicy: IfNotPresent
          
          ports:
            - containerPort: 8080
              name: http
              protocol: TCP
            - containerPort: 8081
              name: management  # Actuator 端口独立
              protocol: TCP
          
          # ===== 环境变量注入 =====
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: "prod"
            - name: NACOS_SERVER_ADDR
              valueFrom:
                configMapKeyRef:
                  name: common-config
                  key: nacos-addr
            - name: NACOS_NAMESPACE
              valueFrom:
                configMapKeyRef:
                  name: common-config
                  key: nacos-namespace
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
            # 容器内获取 Pod 信息
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
          
          # ===== JVM 参数 =====
          env:
            - name: JAVA_OPTS
              value: >-
                -XX:+UseContainerSupport
                -XX:MaxRAMPercentage=75.0
                -XX:+UseG1GC
                -XX:MaxGCPauseMillis=200
                -Dspring.cloud.nacos.discovery.ip=$(POD_IP)
          
          # ===== 资源限制 =====
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          
          # ===== 启动探针（Spring Boot 启动慢时必加）=====
          startupProbe:
            httpGet:
              path: /actuator/health/liveness
              port: management
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 30   # 最多等 150 秒启动
          
          # ===== 存活探针 =====
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: management
            periodSeconds: 15
            failureThreshold: 3
            timeoutSeconds: 5
          
          # ===== 就绪探针 =====
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: management
            periodSeconds: 10
            failureThreshold: 3
            timeoutSeconds: 5
          
          # ===== 优雅停机 =====
          lifecycle:
            preStop:
              exec:
                command: ["sh", "-c", "sleep 5"]
                # 让 K8s 先从 Service Endpoints 摘除，再停进程
          
          # ===== 挂载卷 =====
          volumeMounts:
            - name: config-volume
              mountPath: /app/config
              readOnly: true
      
      volumes:
        - name: config-volume
          configMap:
            name: order-service-config
```

### 2. 启动探针的必要性

Spring Cloud 应用启动时需要做的事情很多：

```
JVM 启动 (~3s)
  → Spring 容器初始化 (~5-15s)
    → Nacos 注册中心连接 (~2-5s)
      → 配置拉取 (~1-3s)
        → Bean 初始化 (~5-20s)
          → Ribbon 路由表加载
            → 就绪
```

**总启动时间可能 30-60 秒甚至更长。** 如果不加 `startupProbe`，`livenessProbe` 会在启动过程中判定失败，导致 K8s 反复杀掉 Pod → 重新拉起 → 又被杀，陷入 `CrashLoopBackOff`。

### 3. Service 与服务发现的配合

```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: microservice
spec:
  selector:
    app: order-service
  ports:
    - name: http
      port: 8080
      targetPort: 8080
    - name: management
      port: 8081
      targetPort: 8081
  type: ClusterIP
```

**两种服务发现模式的对比：**

```
模式一：K8s 原生 Service Discovery
┌────────────┐     DNS      ┌────────────┐
│ Service A  │ ──────────→  │ Service B  │
└────────────┘  k8s svc DNS  └────────────┘
  (kube-proxy / CoreDNS 负责负载均衡)

模式二：Nacos Service Discovery（Spring Cloud 原生）
┌────────────┐    注册/心跳   ┌────────────┐
│ Service A  │ ←───────────→ │   Nacos    │
└────────────┘               └────────────┘
     │  发现实例列表               ↑ 注册/心跳
     │  Ribbon/LoadBalancer 负载均衡
     ▼                        ┌────────────┐
  直连 Pod IP:Port  ────────→ │ Service B  │
                               └────────────┘
```

**关键区别：**

| 维度 | K8s Service | Nacos |
|------|-------------|-------|
| 负载均衡位置 | kube-proxy (iptables/IPVS) | 客户端 Ribbon/Spring Cloud LoadBalancer |
| 健康检查 | K8s Probe | Nacos 心跳 + 临时实例 |
| 流量控制 | 需要 Istio/Linkerd | Nacos 权重 + Sentinel |
| 灰度发布 | 需要 Service Mesh | Nacos metadata 路由 |

**在 K8s 上运行 Spring Cloud 的推荐方案：** 两种共存。K8s Service 作为基础网络通道，Nacos 继续负责 Spring Cloud 生态的服务治理能力（熔断、限流、灰度）。注册到 Nacos 的 IP 使用 Pod IP（非 Node IP），通过环境变量注入。

---

## 三、中间件的容器化部署

### 1. Nacos 集群部署（StatefulSet）

Nacos 有状态，必须用 StatefulSet：

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nacos
  namespace: middleware
spec:
  serviceName: nacos-headless
  replicas: 3
  selector:
    matchLabels:
      app: nacos
  template:
    metadata:
      labels:
        app: nacos
    spec:
      containers:
        - name: nacos
          image: nacos/nacos-server:v2.3.0
          ports:
            - containerPort: 8848
              name: client
            - containerPort: 9848
              name: grpc
            - containerPort: 9849
              name: grpc-raft
          env:
            - name: MODE
              value: "cluster"
            - name: NACOS_SERVERS
              value: "nacos-0.nacos-headless:8848 nacos-1.nacos-headless:8848 nacos-2.nacos-headless:8848"
            - name: SPRING_DATASOURCE_PLATFORM
              value: "mysql"
            - name: MYSQL_SERVICE_HOST
              valueFrom:
                configMapKeyRef:
                  name: nacos-config
                  key: mysql-host
            - name: MYSQL_SERVICE_DB_NAME
              value: "nacos_config"
            - name: MYSQL_SERVICE_USER
              value: "nacos"
            - name: MYSQL_SERVICE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: nacos-db-secret
                  key: password
            - name: JVM_XMS
              value: "512m"
            - name: JVM_XMX
              value: "512m"
          volumeMounts:
            - name: nacos-data
              mountPath: /home/nacos/data
  
  # 持久化存储
  volumeClaimTemplates:
    - metadata:
        name: nacos-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: "ssd-storage"
        resources:
          requests:
            storage: 10Gi

---
# Headless Service（StatefulSet 必须配套）
apiVersion: v1
kind: Service
metadata:
  name: nacos-headless
  namespace: middleware
spec:
  clusterIP: None
  selector:
    app: nacos
  ports:
    - port: 8848
      name: client
    - port: 9848
      name: grpc
    - port: 9849
      name: grpc-raft
```

**StatefulSet 的 DNS 规则：**
```
nacos-0.nacos-headless.middleware.svc.cluster.local
nacos-1.nacos-headless.middleware.svc.cluster.local
nacos-2.nacos-headless.middleware.svc.cluster.local
```

每个 Pod 有稳定的网络标识，Nacos 集群节点间通过 Raft 协议通信，节点名必须固定。

### 2. Sentinel Dashboard 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-dashboard
  namespace: middleware
spec:
  replicas: 1  # Dashboard 只是管理界面，单点即可
  selector:
    matchLabels:
      app: sentinel-dashboard
  template:
    metadata:
      labels:
        app: sentinel-dashboard
    spec:
      containers:
        - name: sentinel
          image: bladex/sentinel-dashboard:1.8.7
          ports:
            - containerPort: 8858
          env:
            - name: JAVA_OPT
              value: "-Xmx256m -Xms256m"
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

### 3. Seata Server 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: seata-server
  namespace: middleware
spec:
  replicas: 2  # 高可用
  selector:
    matchLabels:
      app: seata-server
  template:
    metadata:
      labels:
        app: seata-server
    spec:
      containers:
        - name: seata
          image: seataio/seata-server:1.7.1
          ports:
            - containerPort: 8091
              name: rpc
            - containerPort: 7091
              name: console
          env:
            - name: SEATA_PORT
              value: "8091"
            - name: STORE_MODE
              value: "db"
            - name: SEATA_CONFIG_NAME
              value: "file:/seata-server/resources/application.yml"
          volumeMounts:
            - name: seata-config
              mountPath: /seata-server/resources/application.yml
              subPath: application.yml
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
      volumes:
        - name: seata-config
          configMap:
            name: seata-server-config
```

### 4. RocketMQ 雨署（NameServer + Broker）

```yaml
# NameServer - 无状态，简单 Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rocketmq-namesrv
  namespace: middleware
spec:
  replicas: 2
  selector:
    matchLabels:
      app: namesrv
  template:
    metadata:
      labels:
        app: namesrv
    spec:
      containers:
        - name: namesrv
          image: apache/rocketmq:5.1.4
          command: ["sh", "mqnamesrv"]
          ports:
            - containerPort: 9876
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"

---
# Broker - 有状态，用 StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: rocketmq-broker
  namespace: middleware
spec:
  serviceName: broker-headless
  replicas: 2
  selector:
    matchLabels:
      app: broker
  template:
    metadata:
      labels:
        app: broker
    spec:
      containers:
        - name: broker
          image: apache/rocketmq:5.1.4
          command: ["sh", "mqbroker", "-n", "rocketmq-namesrv:9876", "-c", "/home/rocketmq/rocketmq-5.1.4/conf/broker.conf"]
          ports:
            - containerPort: 10911
              name: broker
            - containerPort: 10909
              name: ha
          env:
            - name: BROKER_ID
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
          volumeMounts:
            - name: broker-data
              mountPath: /home/rocketmq/store
            - name: broker-config
              mountPath: /home/rocketmq/rocketmq-5.1.4/conf/broker.conf
              subPath: broker.conf
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
      volumes:
        - name: broker-config
          configMap:
            name: broker-config
  volumeClaimTemplates:
    - metadata:
        name: broker-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: "ssd-storage"
        resources:
          requests:
            storage: 50Gi
```

---

## 四、K8s 上的网络与通信细节

### Pod 间通信链路

```
┌──────────┐  HTTP/gRPC   ┌──────────┐
│ order-pod│ ──────────→  │ user-pod │
│ 10.244.1.5│             │10.244.2.8│
└──────────┘              └──────────┘
      │                        │
      │   注册到 Nacos          │
      ▼                        ▼
   ┌──────────────────────────────┐
   │         Nacos Cluster        │
   │   10.244.3.2 : 10.244.3.3   │
   │   10.244.3.4                 │
   └──────────────────────────────┘
```

**核心点：** Pod IP 在 K8s 集群内是可路由的（CNI 插件如 Calico/Flannel 负责），Spring Cloud 服务间直连 Pod IP，不经过 K8s Service（除非你选择 K8s 原生服务发现）。

---

## 五、ConfigMap 和 Secret 管理配置

```yaml
# 公共配置
apiVersion: v1
kind: ConfigMap
metadata:
  name: common-config
  namespace: microservice
data:
  nacos-addr: "nacos-headless.middleware:8848"
  nacos-namespace: "production"
  sentinel-dashboard: "sentinel-dashboard.middleware:8858"
  rocketmq-addr: "rocketmq-namesrv.middleware:9876"
  seata-tx-group: "my_tx_group"

---
# 敏感信息
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: microservice
type: Opaque
data:
  username: cm9vdA==          # base64(root)
  password: cEBzc3cwcmQxMjM=  # base64(p@ssw0rd123)
```

```java
// Spring Boot 中通过环境变量消费
@Value("${spring.cloud.nacos.discovery.server-addr}")
private String nacosAddr;  // 来自 ConfigMap
```

```yaml
# application.yml 中引用
spring:
  cloud:
    nacos:
      discovery:
        server-addr: ${NACOS_SERVER_ADDR}
        namespace: ${NACOS_NAMESPACE}
```

---

## 六、完整部署拓扑图

```
┌─────────────────────── K8s Cluster ───────────────────────┐
│                                                            │
│  ┌─── namespace: middleware ────────────────────────────┐  │
│  │                                                      │  │
│  │  [Nacos StatefulSet x3]   [Sentinel Dashboard x1]   │  │
│  │  [Seata Server x2]        [RocketMQ Namesrv x2]     │  │
│  │  [RocketMQ Broker StatefulSet x2]                   │  │
│  │  [SkyWalking OAP x2]      [SkyWalking UI x1]        │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─── namespace: microservice ──────────────────────────┐  │
│  │                                                      │  │
│  │  [Gateway Deployment x2]                             │  │
│  │  [Order Service Deployment x3]                       │  │
│  │  [User Service Deployment x3]                        │  │
│  │  [Inventory Service Deployment x3]                   │  │
│  │  [Payment Service Deployment x3]                     │  │
│  │  [Notification Service Deployment x2]                │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─── namespace: monitoring ────────────────────────────┐  │
│  │                                                      │  │
│  │  [Prometheus x1]        [Grafana x1]                 │  │
│  │  [ELK Stack]            [Jaeger]                     │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─── Ingress Controller ──────────────────────────────┐   │
│  │  [Nginx Ingress / Traefik]                          │   │
│  │  客户端 → Ingress → Gateway Service → Pod           │   │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## 七、CI/CD 流水线构建流程

```
开发者 push 代码
      │
      ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  GitLab CI  │ →  │ Maven Build  │ →  │ Docker Build │
│  / Jenkins  │    │ + Unit Test  │    │ + Push 镜像   │
└─────────────┘    └──────────────┘    └──────┬───────┘
                                              │
                                              ▼
                                      ┌──────────────┐
                                      │ 更新 K8s      │
                                      │ Deployment   │
                                      │ image tag    │
                                      └──────┬───────┘
                                             │
                                             ▼
                                   ┌──────────────────┐
                                   │ Rolling Update   │
                                   │ 新 Pod 启动      │
                                   │ → 就绪探针通过    │
                                   │ → 旧 Pod 下线    │
                                   └──────────────────┘
```

```bash
# 典型的 CI 流水线命令
mvn clean package -DskipTests
docker build -t registry.example.com/micro/order-service:${GIT_SHA:0:8} .
docker push registry.example.com/micro/order-service:${GIT_SHA:0:8}
kubectl set image deployment/order-service \
  order-service=registry.example.com/micro/order-service:${GIT_SHA:0:8} \
  -n microservice
```

---

## 总结

Spring Cloud 微服务上 K8s 的核心底层要点：

| 层次 | 关注点 |
|------|--------|
| **Docker 镜像** | 分层缓存、多阶段构建、JVM 容器适配参数、非 root 运行 |
| **K8s Pod** | 三探针（startup/liveness/readiness）、资源限制、优雅停机、环境变量注入 |
| **K8s 编排** | Deployment（无状态服务）、StatefulSet（有状态中间件）、Headless Service |
| **服务发现** | Nacos 注册 Pod IP、K8s Service DNS 作为备选通道 |
| **配置管理** | ConfigMap + Secret → 环境变量 → Spring 属性注入 |
| **中间件部署** | Nacos/Seata/MQ 各自独立 namespace，有状态组件用 PV 持久化 |

如果你对某个环节想更深入（比如 Seata 在 K8s 上的高可用方案、SkyWalking Agent 无侵入接入、或者 HPA 自动扩缩容策略），可以继续聊。
