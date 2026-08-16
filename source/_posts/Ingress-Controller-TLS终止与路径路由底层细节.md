---
title: Ingress Controller TLS 终止与路径路由的底层细节
date: 2026-09-07 15:00:00
tags:
  - Kubernetes
  - Ingress
  - TLS
  - Nginx
categories:
  - Kubernetes
---

## 一、整体链路全景

```
客户端（浏览器/curl）
  │
  │ ① DNS 解析: api.adcd.com → Ingress Controller External IP
  │
  │ ② TCP 三次握手 → Ingress Controller Pod（Nginx）
  │
  │ ③ TLS 握手（证书验证、密钥协商）
  │
  │ ④ HTTPS 请求: GET /users/123
  │
  │ ⑤ Nginx 路径匹配 → upstream user-service:8080
  │
  │ ⑥ kube-proxy DNAT → Pod IP
  │
  │ ⑦ HTTP 明文转发到后端 Pod
  │
  ▼
user-service Pod 处理请求
```

---

## 二、TLS 终止的底层细节

### 2.1 TLS 证书的存储与挂载

```yaml
# 证书以 Secret 形式存储在 K8s 中
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
  namespace: production
type: kubernetes.io/tls
data:
  tls.crt: <base64 编码的证书链>   # 包含服务器证书 + 中间证书
  tls.key: <base64 编码的私钥>
```

**Ingress Controller 如何获取证书**：

```
Ingress Controller（以 Nginx Ingress 为例）
  │
  ├── ① watch API Server 中所有 Ingress 资源的变化
  │
  ├── ② 当发现 Ingress 配置了 tls 字段时：
  │     ├── 从对应的 Secret 中读取 tls.crt 和 tls.key
  │     ├── 将证书和密钥写入 Pod 本地文件系统
  │     │     /etc/nginx-ssl/default/tls-secret-tls.crt
  │     │     /etc/nginx-ssl/default/tls-secret-tls.key
  │     └── 生成 Nginx 配置中的 ssl_certificate 和 ssl_certificate_key 指令
  │
  ├── ③ 生成 nginx.conf 并 reload Nginx
  │
  └── ④ 持续 watch，证书更新时自动热更新
```

### 2.2 TLS 握手过程（在 Ingress Controller Pod 内完成）

```
                    Client                     Ingress Controller (Nginx Pod)
                      │                                      │
  T+0ms               │──── ClientHello ────────────────────►│
                      │     TLS 1.2/1.3                      │
                      │     支持的密码套件列表                  │
                      │     SNI: api.adcd.com                 │ ← 关键：SNI 字段
                      │     随机数                            │
                      │                                      │
  T+1ms               │◄──── ServerHello ───────────────────│
                      │     选定 TLS 版本                     │
                      │     选定密码套件                       │
                      │     随机数                            │
                      │                                      │
  T+2ms               │◄──── Certificate ──────────────────│
                      │     服务器证书（tls.crt）              │
                      │     中间 CA 证书                      │
                      │                                      │
  T+3ms               │◄──── ServerKeyExchange ─────────────││
                      │     DH/ECDH 公钥参数                  │
                      │                                      │
  T+4ms               │◄──── ServerHelloDone ──────────────│
                      │                                      │
  T+5ms               │──── ClientKeyExchange ────────────►│
                      │     客户端 DH/ECDH 公钥               │
                      │                                      │
  T+6ms               │──── ChangeCipherSpec ─────────────►│
                      │──── Finished ─────────────────────►│
                      │                                      │
  T+7ms               │◄──── ChangeCipherSpec ─────────────│
                      │◄──── Finished ─────────────────────│
                      │                                      │
  T+8ms               │                                      │
  ══════════ TLS 握手完成，后续通信使用对称加密 ══════════════
                      │                                      │
  T+9ms               │──── Encrypted: GET /users/123 ────►│
                      │                                      │
                      │              Nginx 解密                │
                      │              得到明文 HTTP 请求          │
                      │              进行路径匹配               │
                      │              转发到后端（明文 HTTP）      │
                      │                                      │
```

### 2.3 SNI（Server Name Indication）机制

```
一个 Ingress Controller Pod 可能同时处理多个域名的 TLS：

  api.adcd.com  → tls-secret-api
  admin.adcd.com → tls-secret-admin
  cdn.adcd.com  → tls-secret-cdn

SNI 的作用：
  TLS 握手时，客户端在 ClientHello 中携带目标域名
  Nginx 根据 SNI 选择对应的证书

  nginx.conf 对应配置：
  
  # 第一个域名
  server {
      listen 443 ssl;
      server_name api.adcd.com;
      ssl_certificate     /etc/nginx-ssl/default/tls-secret-api-tls.crt;
      ssl_certificate_key /etc/nginx-ssl/default/tls-secret-api-tls.key;
      ...
  }
  
  # 第二个域名
  server {
      listen 443 ssl;
      server_name admin.adcd.com;
      ssl_certificate     /etc/nginx-ssl/default/tls-secret-admin-tls.crt;
      ssl_certificate_key /etc/nginx-ssl/default/tls-secret-admin-tls.key;
      ...
  }
  
  # 默认（无匹配 SNI 时）
  server {
      listen 443 ssl default_server;
      ssl_certificate     /etc/nginx-ssl/default/fallback.crt;
      ssl_certificate_key /etc/nginx-ssl/default/fallback.key;
      return 444;
  }
```

### 2.4 TLS 协议版本与密码套件

```yaml
# 通过 ConfigMap 配置 Nginx Ingress 的 TLS 参数
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-ingress-controller
  namespace: ingress-nginx
data:
  # TLS 协议版本
  ssl-protocols: "TLSv1.2 TLSv1.3"
  
  # 密码套件（TLS 1.2）
  ssl-ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384"
  
  # HSTS
  hsts: "true"
  hsts-max-age: "31536000"
  hsts-include-subdomains: "true"
  
  # OCSP Stapling
  enable-ocsp: "true"
  
  # 会话缓存（减少 TLS 握手开销）
  ssl-session-cache-size: "10m"
  ssl-session-timeout: "10m"
  ssl-session-tickets: "true"
```

**对应的 Nginx 配置片段**：

```nginx
server {
    listen 443 ssl http2;
    server_name api.adcd.com;

    ssl_certificate     /etc/nginx-ssl/default/tls-secret-tls.crt;
    ssl_certificate_key /etc/nginx-ssl/default/tls-secret-tls.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 路径路由规则（下面详细分析）
    location /users {
        proxy_pass http://upstream-user-service;
    }

    location /orders {
        proxy_pass http://upstream-order-service;
    }
}
```

---

## 三、路径匹配的底层细节

### 3.1 从 Ingress 资源到 Nginx 配置的转换

```yaml
# 用户编写的 Ingress 资源
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: production
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
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
```

**Ingress Controller 生成的 Nginx 配置**：

```nginx
# Controller 自动生成的 upstream 定义
upstream production-api-adcd-com-user-service-8080 {
    # 从 Endpoints 获取的 Pod IP 列表
    server 10.244.1.5:8080 max_fails=3 fail_timeout=10s;
    server 10.244.2.8:8080 max_fails=3 fail_timeout=10s;
    server 10.244.3.3:8080 max_fails=3 fail_timeout=10s;
    
    keepalive 32;           # 连接池
}

upstream production-api-adcd-com-order-service-8080 {
    server 10.244.1.12:8080;
    server 10.244.2.15:8080;
    keepalive 32;
}

upstream production-api-adcd-com-frontend-80 {
    server 10.244.1.20:80;
    server 10.244.2.22:80;
    keepalive 32;
}

# Server block
server {
    listen 443 ssl http2;
    server_name api.adcd.com;

    ssl_certificate     /etc/nginx-ssl/default/tls-secret-tls.crt;
    ssl_certificate_key /etc/nginx-ssl/default/tls-secret-tls.key;

    # 路径匹配（注意顺序很重要！）
    
    # 精确前缀 /users
    location /users {
        set $namespace      "production";
        set $ingress_name   "api-ingress";
        set $service_name   "user-service";
        set $service_port   "8080";

        proxy_pass http://production-api-adcd-com-user-service-8080;

        # 代理头设置
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID      $req_id;

        # 超时配置
        proxy_connect_timeout 5s;
        proxy_read_timeout    60s;
        proxy_send_timeout    60s;

        # 缓冲配置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 16k;
    }

    location /orders {
        proxy_pass http://production-api-adcd-com-order-service-8080;
        # ... 同上代理头配置
    }

    location / {
        proxy_pass http://production-api-adcd-com-frontend-80;
        # ... 同上代理头配置
    }
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name api.adcd.com;
    return 308 https://$host$request_uri;
}
```

### 3.2 路径匹配的优先级规则

```
Nginx 的 location 匹配规则（按优先级从高到低）：

  1. 精确匹配      = /users        → 只匹配 /users
  2. 前缀匹配优先   ^~ /users      → 匹配 /users 开头的所有路径（优先于正则）
  3. 正则匹配       ~ ^/users/\d+  → 按顺序匹配第一个命中的正则
  4. 普通前缀匹配   /users         → 匹配 /users 开头（但可能被正则覆盖）
  5. 默认           /              → 匹配所有

  K8s Ingress 的 pathType 对应关系：

  ┌──────────────┬───────────────────────────────────────┐
  │ pathType      │ Nginx 对应行为                         │
  ├──────────────┼───────────────────────────────────────┤
  │ Exact         │ location = /users                    │
  │               │ 只匹配 /users，不匹配 /users/123     │
  ├──────────────┼───────────────────────────────────────┤
  │ Prefix        │ location /users                      │
  │               │ 匹配 /users、/users/、/users/123     │
  │               │ 按 / 分段匹配                         │
  ├──────────────┼───────────────────────────────────────┤
  │ Implementation│ Nginx 原生 location 语法               │
  │ Specific      │ 支持正则等高级匹配                      │
  └──────────────┴───────────────────────────────────────┘
```

### 3.3 Prefix 匹配的分段逻辑

```
path: /users    pathType: Prefix

  请求路径              匹配？    原因
  ─────────────────────────────────────
  /users              ✅         精确匹配
  /users/             ✅         前缀匹配
  /users/123          ✅         前缀匹配
  /users/123/orders   ✅         前缀匹配
  /usersdata          ✅         注意！也是前缀匹配
  /userdata           ❌         不是 /users 前缀

⚠️ /usersdata 也会被匹配到！

解决方案一：使用 ImplementationSpecific + 正则
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/use-regex: "true"
  path: /users(/|$)(.*)

解决方案二：使用 Exact 匹配（但灵活性差）
```

### 3.4 rewrite-target 重写机制

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  rules:
    - host: api.adcd.com
      http:
        paths:
          - path: /users(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: user-service
                port:
                  number: 8080
          - path: /orders(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: order-service
                port:
                  number: 8080
```

```
请求转换过程：

  客户端请求: GET https://api.adcd.com/users/123/profile

  Ingress Controller 处理：
    ① 匹配路径: /users(/|$)(.*)
       → 捕获组 $1 = /
       → 捕获组 $2 = 123/profile
    
    ② rewrite-target: /$2
       → 重写为: /123/profile
    
    ③ proxy_pass 到 user-service:8080/123/profile

  后端 Pod 收到的请求: GET /123/profile

  ┌─────────────────────────────────────────────────────┐
  │  Client → Ingress Controller → Backend Pod           │
  │                                                      │
  │  GET /users/123/profile     →  GET /123/profile      │
  │  Host: api.adcd.com           Host: api.adcd.com     │
  └─────────────────────────────────────────────────────┘
```

---

## 四、proxy_pass 转发的底层细节

### 4.1 代理头（Proxy Headers）

```nginx
# Ingress Controller 自动设置的请求头

proxy_set_header Host              $host;
# → 传递原始 Host 头（api.adcd.com），后端 Pod 据此判断来源域名

proxy_set_header X-Real-IP         $remote_addr;
# → 客户端真实 IP（如果前面没有其他代理）

proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
# → 追加当前代理 IP 到已有的 X-Forwarded-For 列表
# → 格式: "client_ip, proxy1_ip, proxy2_ip"

proxy_set_header X-Forwarded-Proto $scheme;
# → 原始协议：https（因为 TLS 在此处终止）

proxy_set_header X-Forwarded-Host  $host;
proxy_set_header X-Forwarded-Port  $server_port;
```

**后端 Pod 看到的完整请求**：

```http
GET /123/profile HTTP/1.1
Host: api.adcd.com
X-Real-IP: 203.0.113.50
X-Forwarded-For: 203.0.113.50
X-Forwarded-Proto: https
X-Forwarded-Host: api.adcd.com
X-Forwarded-Port: 443
X-Request-ID: a1b2c3d4e5f6
User-Agent: Mozilla/5.0 ...
Accept: application/json
```

### 4.2 从 Ingress Pod 到后端 Pod 的网络路径

```
Ingress Controller Pod（Nginx）        后端 Pod（user-service）
     │                                        │
     │  proxy_pass                             │
     │  http://10.244.1.5:8080                 │
     │                                        │
     │  ① DNS 解析 upstream 名称               │
     │     但 Nginx 启动时已解析并写入配置       │
     │     直接使用 Pod IP                      │
     │                                        │
     │  ② 建立 TCP 连接                        │
     │     Ingress Pod → 10.244.1.5:8080      │
     │                                        │
     │     如果同节点：                          │
     │     veth → bridge → veth                │
     │                                        │
     │     如果跨节点：                          │
     │     veth → bridge → tunl0/VXLAN → ...  │
     │                                        │
     │  ③ 发送 HTTP 明文请求                    │
     │     （TLS 已在 Ingress 层终止）          │
     │                                        │
     ▼                                        ▼
```

### 4.3 Upstream Pod IP 的动态更新

```
Ingress Controller 如何感知后端 Pod 变化：

  ① Controller watch API Server 的 Endpoints 资源
  ② 当 user-service 的 Pod 变化（扩缩容/重启/故障）：
     ├── Endpoints 更新（新增/移除 Pod IP）
     ├── Controller 检测到变化
     ├── 重新生成 nginx.conf 中的 upstream 块
     └── 执行 nginx -s reload（热更新，不中断连接）

  nginx -s reload 的底层过程：
  ├── master 进程读取新配置
  ├── 检查配置语法
  ├── 创建新的 worker 进程（使用新配置）
  ├── 通知旧 worker 进程停止接受新连接
  └── 旧 worker 处理完存量请求后退出
```

**reload 不中断连接的原理**：

```
  ┌──────────────┐
  │ Nginx Master │
  │   Process    │
  └──────┬───────┘
         │ fork
    ┌────┴────┐
    ▼         ▼
  ┌──────┐  ┌──────┐
  │Old   │  │New   │
  │Worker│  │Worker│
  │(v1)  │  │(v2)  │
  └──┬───┘  └──┬───┘
     │         │
     │ 处理存量 │ 接收新请求
     │ 请求完毕 │
     │    ↓    │
     │  退出   │ 继续运行
     └─────────┘
```

---

## 五、HTTP → HTTPS 重定向底层

### 5.1 强制 HTTPS

```yaml
# Ingress 配置
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
```

```nginx
# 生成的 Nginx 配置
server {
    listen 80;
    server_name api.adcd.com;
    
    # 308 永久重定向（保留请求方法）
    return 308 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.adcd.com;
    # ... TLS 配置和路由规则
}
```

```
客户端请求过程：

  ① GET http://api.adcd.com/users → 返回 308
  ② 浏览器自动跟随: GET https://api.adcd.com/users
  ③ TLS 握手
  ④ 加密请求到达
  ⑤ Ingress 解密 → 路径匹配 → 转发到后端

  状态码选择：
  301 → 永久重定向，浏览器缓存，POST 会变 GET
  302 → 临时重定向，POST 会变 GET
  307 → 临时重定向，保留方法（推荐临时场景）
  308 → 永久重定向，保留方法（推荐永久场景）
```

---

## 六、流量经过 Ingress Controller 的完整网络路径

```
步骤    网络层     发生的事情                              地址变化
─────────────────────────────────────────────────────────────────────
 ①     应用层     客户端 DNS 解析 api.adcd.com            域名 → LB IP
 ②     传输层     TCP 三次握手到 LB                       Client → LB:443
 ③     传输层     LB 转发到 Node 的 NodePort              LB → Node:30443
 ④     网络层     kube-proxy iptables DNAT                Node:30443 → Ingress Pod:443
 ⑤     应用层     TLS 握手（Nginx Pod 内）                 TLS 终止
 ⑥     应用层     Nginx 解密 HTTP，路径匹配 /users         路由决策
 ⑦     应用层     proxy_pass 到 upstream                  Ingress Pod → 10.244.1.5:8080
 ⑧     网络层     数据包路由到后端 Pod                      CNI 负责
 ⑨     应用层     后端 Pod 处理 HTTP 明文请求               业务逻辑
```

**地址翻译全过程**：

```
客户端看到的：
  源地址:      203.0.113.50:54321 (客户端)
  目标地址:    47.100.1.1:443 (LB)

LB 转发后：
  源地址:      203.0.113.50:54321 (或 LB NAT 后的地址)
  目标地址:    192.168.1.10:30443 (Node)

kube-proxy DNAT 后：
  源地址:      203.0.113.50:54321
  目标地址:    10.244.0.15:443 (Ingress Controller Pod)

Nginx proxy_pass 后：
  源地址:      10.244.0.15:xxxxx (Ingress Pod)
  目标地址:    10.244.1.5:8080 (user-service Pod)

⚠️ 后端 Pod 看到的源 IP：
  - 无 Proxy Protocol: 看到的是 Ingress Pod 的 IP
  - 有 Proxy Protocol: 可以获取真实客户端 IP
```

---

## 七、获取真实客户端 IP

### 7.1 externalTrafficPolicy

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ingress-nginx
  namespace: ingress-nginx
spec:
  type: LoadBalancer
  externalTrafficPolicy: Local    # 关键配置
  selector:
    app.kubernetes.io/name: ingress-nginx
  ports:
    - port: 443
      targetPort: 443
      nodePort: 30443
```

```
externalTrafficPolicy 的影响：

  Cluster（默认）：
    Client → LB → Node_A → iptables DNAT → Node_B:Ingress Pod
    源 IP 变为 Node_A 的 IP ❌

  Local：
    Client → LB → Node_A → 本地 Ingress Pod（不跨节点转发）
    源 IP 保持不变 ✅
    但要求 Ingress Pod 必须运行在接收流量的节点上
```

### 7.2 Proxy Protocol

```yaml
# 启用 Proxy Protocol
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-ingress-controller
  namespace: ingress-nginx
data:
  use-proxy-protocol: "true"
```

```
Proxy Protocol 工作原理：

  LB 在转发 TCP 连接时，在数据最前面插入一行：
  
  PROXY TCP4 203.0.113.50 192.168.1.10 54321 443\r\n
  <原始 HTTP 数据>
  
  Nginx 解析这一行，提取真实客户端 IP：
  → $remote_addr = 203.0.113.50
  → 传递给后端的 X-Real-IP = 203.0.113.50
```

---

## 八、高级路由功能的底层实现

### 8.1 基于 Header 的路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: canary-ingress
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-by-header: "X-Canary"
    nginx.ingress.kubernetes.io/canary-by-header-value: "true"
spec:
  ingressClassName: nginx
  rules:
    - host: api.adcd.com
      http:
        paths:
          - path: /users
            pathType: Prefix
            backend:
              service:
                name: user-service-canary
                port:
                  number: 8080
```

```nginx
# 生成的 Nginx 配置逻辑（伪代码）
map $http_x_canary $canary_header {
    "true"  1;
    default 0;
}

location /users {
    set $target "production-api-adcd-com-user-service-8080";
    
    if ($canary_header) {
        set $target "production-api-adcd-com-user-service-canary-8080";
    }
    
    proxy_pass http://$target;
}
```

### 8.2 基于权重的灰度发布

```yaml
# 主 Ingress（90% 流量）
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: user-service-stable
spec:
  rules:
    - host: api.adcd.com
      http:
        paths:
          - path: /users
            backend:
              service:
                name: user-service-v1
                port:
                  number: 8080
---
# 灰度 Ingress（10% 流量）
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: user-service-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"
spec:
  rules:
    - host: api.adcd.com
      http:
        paths:
          - path: /users
            backend:
              service:
                name: user-service-v2
                port:
                  number: 8080
```

```nginx
# Nginx 内部通过 split_clients 实现
split_clients $request_id $canary_weight {
    10%   production-api-adcd-com-user-service-v2-8080;
    *     production-api-adcd-com-user-service-v1-8080;
}

location /users {
    proxy_pass http://$canary_weight;
}
```

### 8.3 限流

```yaml
annotations:
  nginx.ingress.kubernetes.io/limit-rps: "100"         # 每秒 100 请求
  nginx.ingress.kubernetes.io/limit-rpm: "6000"         # 每分钟 6000 请求
  nginx.ingress.kubernetes.io/limit-connections: "50"    # 最大 50 并发连接
  nginx.ingress.kubernetes.io/limit-whitelist: "10.0.0.0/8"  # 白名单不限流
```

```nginx
# 生成的 Nginx 配置
limit_req_zone $binary_remote_addr zone=rate_limit:10m rate=100r/s;

location /users {
    limit_req zone=rate_limit burst=200 nodelay;
    limit_conn_status 429;
    
    proxy_pass http://upstream-user-service;
}
```

---

## 九、不同 Ingress Controller 实现对比

```
┌──────────────────┬──────────────┬──────────────┬──────────────┐
│ 特性              │ Nginx        │ Traefik      │ Envoy (Contour)│
├──────────────────┼──────────────┼──────────────┼──────────────┤
│ 代理引擎          │ Nginx        │ Traefik      │ Envoy        │
│ 配置重载          │ reload       │ 热更新        │ xDS/热更新    │
│ TLS 终止         │ OpenSSL      │ Go TLS       │ BoringSSL    │
│ HTTP/2           │ ✅            │ ✅            │ ✅            │
│ gRPC 路由        │ ✅            │ ✅            │ ✅（原生）    │
│ 动态配置         │ reload（有    │ 无感          │ xDS（完全     │
│                  │  短暂中断）   │              │  无中断）     │
│ 连接排空         │ reload 期间   │ 无缝          │ xDS 推送      │
│                  │ 旧连接排空    │              │ 连接排空       │
│ 限流             │ nginx 模块    │ 内置          │ ext_authz    │
│ 中间件生态       │ annotation    │ middleware    │ extension    │
└──────────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 十、排查 TLS 与路由问题

```bash
# 1. 检查 Ingress 资源状态
kubectl get ingress api-ingress -n production -o yaml

# 2. 查看 Ingress Controller 日志
kubectl -n ingress-nginx logs -l app.kubernetes.io/name=ingress-nginx --tail=100

# 3. 查看生成的 Nginx 配置
kubectl -n ingress-nginx exec -it <nginx-pod> -- cat /etc/nginx/nginx.conf | grep -A 20 "api.adcd.com"

# 4. 测试 TLS 握手
openssl s_client -connect api.adcd.com:443 -servername api.adcd.com

# 5. 查看证书详情
openssl s_client -connect api.adcd.com:443 -servername api.adcd.com </dev/null 2>/dev/null | openssl x509 -text -noout

# 6. 测试路径路由
curl -v -H "Host: api.adcd.com" https://api.adcd.com/users/123
curl -v -H "Host: api.adcd.com" https://api.adcd.com/orders/456

# 7. 测试灰度路由
curl -H "Host: api.adcd.com" -H "X-Canary: true" https://api.adcd.com/users/123

# 8. 检查 Endpoints
kubectl get endpoints user-service -n production -o wide

# 9. 检查证书 Secret
kubectl get secret tls-secret -n production -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout

# 10. 检查 Ingress Controller 的配置哈希
kubectl -n ingress-nginx exec -it <nginx-pod> -- nginx -T | md5sum
```

如果你们有具体的 Ingress Controller 类型（Nginx/Traefik/Envoy）和当前遇到的 TLS 或路由问题，可以进一步展开排查。
