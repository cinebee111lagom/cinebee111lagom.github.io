---
title: K8s 业务端地址寻址的底层细节分析
date: 2026-09-07 14:30:00
tags:
  - Kubernetes
  - DNS
  - Service
  - 服务发现
categories:
  - Kubernetes
---

## 一、业务端地址体系全景图

当一个业务 Pod（如 `order-service`）需要调用另一个业务 Pod（如 `user-service`）时，涉及的地址层次如下：

```
应用层调用
  │
  ├── ① 域名（业务最关心的）
  │       user-service.default.svc.cluster.local
  │
  ├── ② DNS 解析（CoreDNS 完成）
  │       域名 → ClusterIP（如 10.96.7.23）
  │
  ├── ③ Service 路由（kube-proxy / IPVS / eBPF）
  │       ClusterIP:Port → Pod_IP:TargetPort（如 10.244.1.5:8080）
  │
  ├── ④ CNI 网络送达
  │       Pod_IP 路由到目标容器的 network namespace
  │
  └── ⑤ 容器内进程接收
          应用监听 0.0.0.0:8080
```

---

## 二、域名寻址的完整细节

### 2.1 集群内 Service 域名格式

```
完全限定域名（FQDN）格式：

  <service-name>.<namespace>.svc.cluster.local

各部分含义：
  ┌───────────┬──────────────────────────────────────┐
  │ 部分       │ 说明                                  │
  ├───────────┼──────────────────────────────────────┤
  │ user-svc  │ Service 名称（由运维/开发定义）        │
  │ production│ Namespace 名称                        │
  │ svc       │ 固定标识，表明这是一个 Service          │
  │ cluster   │ 固定标识，表明在集群内                  │
  │ local     │ 固定标识，集群根域名                   │
  └───────────┴──────────────────────────────────────┘
```

### 2.2 不同命名空间下的调用方式

```yaml
# 场景：order-service（在 order-ns）调用 user-service（在 user-ns）

# 方式一：使用 FQDN（最安全、最明确）
jdbc:mysql://user-service.user-ns.svc.cluster.local:3306/users

# 方式二：使用短名称（仅限同 Namespace）
jdbc:mysql://user-service:3306/users

# 方式三：使用简写（依赖 Pod 的 ndots 配置）
jdbc:mysql://user-service.user-ns:3306/users
```

**为什么不推荐用短名称跨 Namespace？**

```
order-service 的 /etc/resolv.conf：

  nameserver 10.96.0.10
  search order-ns.svc.cluster.local svc.cluster.local cluster.local
  ndots:5

当 order-service 解析 "user-service" 时：
  → 先搜索 order-ns.svc.cluster.local 中有没有 user-service
  → 不在 order-ns 中，再搜索 svc.cluster.local
  → 最终可能找不到或找到错误的 Service

使用 FQDN "user-service.user-ns.svc.cluster.local"：
  → ndots=5，包含 4 个点 < 5，直接查询（不走 search 域）
  → CoreDNS 直接返回正确结果
```

### 2.3 Pod 级别的 DNS 记录

```yaml
# StatefulSet 的 Pod 有固定 DNS
# 格式：<pod-name>.<headless-service>.<namespace>.svc.cluster.local

# 业务调用示例（直接连接特定 Pod）：
redis://redis-0.redis-headless.production.svc.cluster.local:6379
redis://redis-1.redis-headless.production.svc.cluster.local:6379

# Deployment 的 Pod 无固定 DNS，只能通过 Service 访问
# 格式：ip-<ip-with-dashes>.<namespace>.pod.cluster.local
# 例：ip-10-244-1-5.production.pod.cluster.local
```

---

## 三、业务端代码中的地址配置

### 3.1 应用配置文件示例

```yaml
# Spring Boot application.yml
spring:
  datasource:
    # 使用 Service 域名访问 MySQL
    url: jdbc:mysql://mysql-headless.production.svc.cluster.local:3306/order_db
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
  
  redis:
    # 使用 Service 域名访问 Redis
    host: redis.production.svc.cluster.local
    port: 6379

  kafka:
    # 使用 Headless Service 访问 Kafka（直连每个 Broker）
    bootstrap-servers:
      - kafka-0.kafka-headless.production.svc.cluster.local:9092
      - kafka-1.kafka-headless.production.svc.cluster.local:9092
      - kafka-2.kafka-headless.production.svc.cluster.local:9092

# 微服务间 HTTP 调用
user-service:
  url: http://user-service.production.svc.cluster.local:8080

payment-service:
  url: http://payment-service.production.svc.cluster.local:8080
```

### 3.2 通过环境变量注入地址

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  template:
    spec:
      containers:
        - name: order
          image: order-service:v2.1
          env:
            # 方式一：直接注入 Service 地址
            - name: USER_SERVICE_URL
              value: "http://user-service.production.svc.cluster.local:8080"
            
            # 方式二：通过 Downward API 注入自身信息
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
            - name: NODE_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
            - name: NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            
            # 方式三：通过 ConfigMap 注入
            - name: DB_HOST
              valueFrom:
                configMapKeyRef:
                  name: app-config
                  key: database-host
            
            # 方式四：通过 Secret 注入敏感信息
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
```

### 3.3 K8s 自动注入的环境变量

```
当 user-service 先于 order-service 创建时，
K8s 会自动为 order-service 注入 user-service 的环境变量：

  USER_SERVICE_SERVICE_HOST=10.96.7.23
  USER_SERVICE_SERVICE_PORT=8080
  USER_SERVICE_PORT=tcp://10.96.7.23:8080
  USER_SERVICE_PORT_8080_TCP=tcp://10.96.7.23:8080
  USER_SERVICE_PORT_8080_TCP_PROTO=tcp
  USER_SERVICE_PORT_8080_TCP_PORT=8080
  USER_SERVICE_PORT_8080_TCP_ADDR=10.96.7.23

命名规则：
  <SERVICE_NAME>_SERVICE_HOST
  <SERVICE_NAME>_SERVICE_PORT
  （Service 名称中的 - 被替换为 _，字母大写）

⚠️ 问题：
  - 仅在 Service 先创建的情况下注入
  - 依赖顺序，不可靠
  - DNS 方式更推荐
```

---

## 四、DNS 解析的底层链路

### 4.1 Pod 的 resolv.conf

```bash
# 进入任意 Pod 查看
kubectl exec -it order-pod -- cat /etc/resolv.conf

# 输出：
nameserver 10.96.0.10                    # CoreDNS 的 ClusterIP
search production.svc.cluster.local      # 当前 Namespace 的搜索域
           svc.cluster.local             # 所有 Service 的搜索域
           cluster.local                 # 集群根域
ndots:5                                   # 点数阈值
```

### 4.2 ndots 的影响（关键！）

```
ndots:5 的含义：
  如果域名中包含的点数 < 5，则先拼接 search 域后缀逐一查询
  如果域名中包含的点数 >= 5，则直接查询该域名

举例：
  解析 "user-service"
    → 点数 0 < 5
    → 先查 user-service.production.svc.cluster.local（拼第一个 search）
    → 如果找不到，继续拼下一个 search 域
    → 最后尝试直接查询 user-service

  解析 "user-service.production.svc.cluster.local"
    → 点数 4 < 5
    → 先拼 search 域！ user-service.production.svc.cluster.local.production.svc.cluster.local
    → 这个肯定查不到
    → 再尝试 FQDN 本身 → 查到了
    
  解析 "external.api.example.com"
    → 点数 3 < 5
    → 先拼 search 域 → 都查不到
    → 最后直接查询 → 成功

⚠️ 性能影响：
  每次查询一个 FQDN 会先产生 3 次无效的 search 域查询
  → 产生大量无效 DNS 请求
  → 可能导致 DNS 延迟甚至超时
```

### 4.3 DNS 解析全流程

```
order-service 调用 user-service.production.svc.cluster.local:8080

  应用层
    │
    │ socket.connect("user-service.production.svc.cluster.local", 8080)
    │
    ▼
  libc getaddrinfo()
    │
    │ 检查域名点数：
    │   4 个点 < ndots(5)
    │   → 先走 search 域
    │
    │ 第 1 次查询：user-service.production.svc.cluster.local.production.svc.cluster.local
    │   → CoreDNS 查 A 记录 → NXDOMAIN
    │
    │ 第 2 次查询：user-service.production.svc.cluster.local.svc.cluster.local
    │   → CoreDNS 查 A 记录 → NXDOMAIN
    │
    │ 第 3 次查询：user-service.production.svc.cluster.local.cluster.local
    │   → CoreDNS 查 A 记录 → NXDOMAIN
    │
    │ 第 4 次查询：user-service.production.svc.cluster.local（原始名称）
    │   → CoreDNS 查 A 记录 → 命中！
    │   → 返回 ClusterIP: 10.96.7.23
    │
    ▼
  内核 TCP 连接
    │
    │ 目标 IP: 10.96.7.23（ClusterIP）
    │ 目标端口: 8080
    │
    ▼
  iptables/IPVS DNAT
    │
    │ 改写目标为: 10.244.1.5:8080（某个后端 Pod）
    │
    ▼
  路由到目标 Pod
```

### 4.4 优化 DNS 性能

```yaml
# 方案一：在 Pod Spec 中自定义 dnsConfig
apiVersion: v1
kind: Pod
spec:
  dnsConfig:
    options:
      - name: ndots
        value: "2"          # 降低 ndots，减少无效查询
      - name: single-request-reopen  # 解决 DNS 并发查询丢包问题
      - name: timeout
        value: "2"          # DNS 超时时间

# 方案二：使用 FQDN（包含足够多的点，跳过 search 域）
# ndots:5 的情况下，FQDN 有 4 个点仍会走 search 域
# 如果应用代码中直接写 FQDN，设置 ndots:2 可以避免这个问题
```

---

## 五、Service 类型与业务端地址选择

### 5.1 ClusterIP（集群内访问）

```yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
spec:
  type: ClusterIP
  # clusterIP: None    # Headless 模式
  selector:
    app: user-service
  ports:
    - port: 80          # Service 端口
      targetPort: 8080  # Pod 端口
```

```
业务端访问地址：
  http://user-service:8080
  http://user-service.production.svc.cluster.local:8080

注意：port 和 targetPort 不同时
  业务代码连接的是 port（80）
  kube-proxy DNAT 后转到 targetPort（8080）
```

### 5.2 Headless Service（直连 Pod）

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kafka-headless
spec:
  clusterIP: None
  selector:
    app: kafka
  ports:
    - port: 9092
```

```
DNS 解析结果（返回所有 Pod IP）：

  $ nslookup kafka-headless.production.svc.cluster.local
  
  Name:    kafka-headless.production.svc.cluster.local
  Address: 10.244.1.5    ← kafka-0
  Address: 10.244.2.8    ← kafka-1
  Address: 10.244.3.3    ← kafka-2

业务端连接：
  Kafka、Elasticsearch 等需要知道所有节点地址
  → 客户端直接管理连接池和负载均衡
  → 绕过 kube-proxy，性能更高
```

### 5.3 NodePort / LoadBalancer（集群外访问）

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
spec:
  type: LoadBalancer
  ports:
    - port: 443
      targetPort: 8443
      nodePort: 30443     # 节点端口范围：30000-32767
```

```
集群外访问地址：

  NodePort：
    http://<node-ip>:30443
    所有节点（包括 Master）都会监听 30443

  LoadBalancer：
    https://<external-lb-ip>:443
    → 云厂商自动创建外部负载均衡器
    → 转发到节点的 NodePort
    → 再 DNAT 到 Pod

  实际路径：
    Client → LB → Node:NodePort → iptables DNAT → Pod:TargetPort
```

### 5.4 ExternalName（外部服务 CNAME）

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-mysql
  namespace: production
spec:
  type: ExternalName
  externalName: rds-mysql.xxx.rds.aliyuncs.com
```

```
业务端访问：
  jdbc:mysql://external-mysql.production.svc.cluster.local:3306/mydb
  → DNS 解析为 CNAME → rds-mysql.xxx.rds.aliyuncs.com
  → 再解析为外部 IP
  → 直接出集群访问外部 RDS

用途：把外部服务"伪装"成集群内 Service，统一地址管理
```

---

## 六、Service Mesh 下的地址细节（Istio）

### 6.1 Sidecar 代理拦截

```
开启 Istio 注入后，Pod 内增加 envoy sidecar：

  ┌─────────────────────────────────────┐
  │              Pod                     │
  │                                      │
  │  ┌──────────┐    ┌───────────────┐  │
  │  │ business │    │ envoy sidecar │  │
  │  │ app      │    │ (istio-proxy) │  │
  │  │          │    │               │  │
  │  │ connect()├───►│ iptables REDIRECT
  │  │          │    │ :15001 inbound│  │
  │  └──────────┘    │ :15006 outbound│ │
  │                  └───────────────┘  │
  └─────────────────────────────────────┘
```

**地址变化**：

```
无 Mesh 时：
  App → user-service:8080 → CoreDNS → ClusterIP → DNAT → Pod

有 Mesh 时：
  App → user-service:8080 → iptables REDIRECT → envoy sidecar
        → 做 mTLS、负载均衡、重试、熔断
        → 选择目标 Pod（通过 EDS/Envoy endpoint）
        → 直接连接目标 Pod IP:8080（跳过 kube-proxy）
```

### 6.2 VirtualService 地址路由

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: user-service
spec:
  hosts:
    - user-service.production.svc.cluster.local
  http:
    # 90% 流量到 v2
    - match:
        - headers:
            x-canary:
              exact: "true"
      route:
        - destination:
            host: user-service.production.svc.cluster.local
            subset: v3
    
    - route:
        - destination:
            host: user-service.production.svc.cluster.local
            subset: v2
          weight: 90
        - destination:
            host: user-service.production.svc.cluster.local
            subset: v1
          weight: 10
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: user-service
spec:
  host: user-service.production.svc.cluster.local
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
    - name: v3
      labels:
        version: v3
```

```
业务端地址不变：
  http://user-service:8080

但实际路由由 Istio 控制：
  → 90% 到 version=v2 的 Pod
  → 10% 到 version=v1 的 Pod
  → 带 x-canary header 到 version=v3 的 Pod
```

---

## 七、Ingress — 集群入口地址

### 7.1 Ingress 路由规则

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.adcd.com
      secretName: tls-secret
  rules:
    - host: api.adcd.com
      http:
        paths:
          - path: /users
            pathType: Prefix
            backend:
              service:
                name: user-service
                port:
                  number: 8080
          
          - path: /orders
            pathType: Prefix
            backend:
              service:
                name: order-service
                port:
                  number: 8080
          
          - path: /payments
            pathType: Prefix
            backend:
              service:
                name: payment-service
                port:
                  number: 8080
```

```
外部客户端访问路径：

  https://api.adcd.com/users
    │
    ├── DNS 解析 → Ingress Controller 的外部 IP（如 47.100.x.x）
    │
    ├── TLS 终止（Ingress Controller）
    │
    ├── 路径匹配 /users → user-service:8080
    │
    ├── kube-proxy DNAT → user-service Pod IP
    │
    └── Pod 处理请求
```

### 7.2 Gateway API（新一代）

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: user-route
spec:
  parentRefs:
    - name: main-gateway
  hostnames:
    - "api.adcd.com"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /users
      backendRefs:
        - name: user-service
          port: 8080
          weight: 90
        - name: user-service-canary
          port: 8080
          weight: 10
```

---

## 八、业务端连接管理最佳实践

### 8.1 连接池配置

```yaml
# Spring Boot 连接池配置
spring:
  datasource:
    url: jdbc:mysql://mysql-headless.production.svc.cluster.local:3306/order_db
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000     # 30 秒
      idle-timeout: 600000          # 10 分钟
      max-lifetime: 1800000         # 30 分钟
      
      # K8s 环境关键配置
      validation-timeout: 5000
      leak-detection-threshold: 60000
```

### 8.2 DNS 缓存问题

```
⚠️ 业务端常见陷阱：DNS 缓存导致流量不均衡

Java 应用：
  JVM 默认永久缓存 DNS 解析结果
  → Service 的 ClusterIP 变化后（极端情况），Java 仍然使用旧 IP
  
  解决方案：
  # JVM 参数
  -Dnetworkaddress.cache.ttl=30        # 成功缓存 30 秒
  -Dnetworkaddress.cache.negative.ttl=10  # 失败缓存 10 秒

Go 应用：
  Go 默认不缓存 DNS（每次调用 getaddrinfo）
  → 无此问题，但高频调用会产生大量 DNS 请求

Python 应用：
  使用 socket.getaddrinfo()，受 glibc 缓存影响
  → 可通过 resolv.conf 的 options 配置
```

### 8.3 超时与重试

```yaml
# 推荐的超时链路
业务端调用配置：
  连接超时（Connection Timeout）:  3-5 秒
  读取超时（Read Timeout）:        10-30 秒
  重试次数（Max Retries）:          2-3 次
  重试间隔（Retry Backoff）:        指数退避

# 与 K8s 组件的超时关系
  kubelet readinessProbe:     periodSeconds=10, failureThreshold=3
  → 一个 Pod 不健康后，最慢 30 秒从 Endpoints 中移除
  → 期间仍可能有流量打到不健康的 Pod
  → 业务端必须做超时和重试
```

### 8.4 健康检查与优雅关闭配合

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: order-service
          image: order-service:v2.1
          
          # 就绪探针：决定是否接收流量
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 3
          
          # 存活探针：决定是否重启
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 3
          
          # 优雅关闭：处理存量请求
          lifecycle:
            preStop:
              exec:
                command: ["sh", "-c", "sleep 10"]
                # sleep 让 Endpoints 更新生效后再停止接收新请求
          
          terminationGracePeriodSeconds: 60
```

**关闭时序**：

```
时间线（Pod 被删除时）：

  T+0s   收到 SIGTERM
         preStop 开始执行（sleep 10）
         Pod 状态 → Terminating
         
  T+0s   Endpoints Controller 移除该 Pod IP
         但更新有传播延迟（kube-proxy / CoreDNS / 客户端连接池）
         
  T+10s  preStop 完成
         应用开始关闭（Spring Boot shutdown hook）
         处理存量请求，拒绝新请求
         
  T+60s  terminationGracePeriodSeconds 到期
         SIGKILL 强制终止

关键：sleep 10 让 Endpoints 更新有足够时间传播到所有客户端
```

---

## 九、完整的业务端调用链路图

```
外部用户请求
  │
  ▼
DNS 解析: api.adcd.com → Ingress Controller IP (47.100.x.x)
  │
  ▼
Ingress Controller (Nginx / Traefik)
  │ TLS 终止
  │ 路径路由: /orders → order-service:8080
  ▼
order-service Pod
  │ readinessProbe OK，正在接收流量
  │
  │ 业务逻辑处理中...
  │ 需要查询用户信息
  │
  ├── DNS 查询: user-service.production.svc.cluster.local
  │     → CoreDNS → 10.96.7.23 (ClusterIP)
  │
  ├── HTTP 调用: http://user-service:8080/api/users/123
  │     → iptables DNAT → 10.244.1.5:8080 (user-service Pod)
  │
  ├── 需要查询订单数据
  │     DNS 查询: mysql-headless.production.svc.cluster.local
  │     → CoreDNS → [10.244.1.10, 10.244.2.11, 10.244.3.12]
  │
  ├── JDBC 连接: mysql-headless:3306/order_db
  │     → 直连 Pod（Headless Service，跳过 kube-proxy）
  │
  ├── 需要缓存查询结果
  │     DNS 查询: redis.production.svc.cluster.local
  │     → CoreDNS → 10.96.15.88 (ClusterIP)
  │
  ├── Redis 调用: redis:6379
  │     → kube-proxy DNAT → 10.244.2.20:6379 (redis Pod)
  │
  └── 返回响应给用户
```

---

## 十、排查业务端地址问题

```bash
# 1. 从 Pod 内测试 DNS
kubectl exec -it order-pod -- nslookup user-service.production.svc.cluster.local
kubectl exec -it order-pod -- nslookup user-service   # 短名称

# 2. 查看 Pod 的 resolv.conf
kubectl exec -it order-pod -- cat /etc/resolv.conf

# 3. 从 Pod 内测试 TCP 连通性
kubectl exec -it order-pod -- curl -v http://user-service:8080/health
kubectl exec -it order-pod -- nc -zv user-service 8080

# 4. 检查 Service 的 Endpoints
kubectl get endpoints user-service -o yaml

# 5. 检查 DNS 日志（CoreDNS）
kubectl -n kube-system logs -l k8s-app=kube-dns --tail=100

# 6. 抓包分析
kubectl exec -it order-pod -- tcpdump -i eth0 -nn port 53 -c 20    # DNS 抓包
kubectl exec -it order-pod -- tcpdump -i eth0 -nn host 10.96.7.23  # Service 流量抓包

# 7. 检查 conntrack
conntrack -L -p tcp --dport 8080 | grep 10.96.7.23
```

如果你们有具体的业务服务架构和当前遇到的地址/连通性问题，可以进一步深入分析。
