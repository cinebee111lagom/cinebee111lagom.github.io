---
title: Istio/Envoy 端口识别的底层细节
date: 2026-09-07 13:15:00
tags:
  - Istio
  - Envoy
  - Service Mesh
  - Kubernetes
categories:
  - Kubernetes
---

## 一、端口识别的全局流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        端口识别完整链路                                │
│                                                                      │
│  K8s Service Port Name    ──┐                                       │
│  (e.g. "http-myapp")        │                                       │
│                              ├──▶  Pilot (Istiod) 生成 xDS 配置     │
│  Auto Protocol Detection     │      │                                │
│  (嗅探前几个字节)             ──┘      ▼                                │
│                              Envoy 收到 LDS/RDS/CDS/EDS 推送       │
│                                        │                            │
│                                        ▼                            │
│                              Envoy 构建 Filter Chain                │
│                              ├── HTTP Connection Manager (L7)       │
│                              ├── TCP Proxy (L4)                     │
│                              ├── Mongo/Thrift/Redis (L7 专用)       │
│                              └── TLS Inspector (先嗅探 TLS)         │
│                                        │                            │
│                                        ▼                            │
│                              数据包到达 → Filter Chain 匹配执行      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、端口命名约定 — Istio 的第一层协议识别

### 2.1 Istio 识别的端口名前缀

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  selector:
    app: my-app
  ports:
    # Istio 通过 port.name 前缀判断 L7 协议
    - name: http-api        # ← "http-" 前缀 → HTTP/1.1 + HTTP/2
      port: 80
      targetPort: 8080

    - name: http2-grpc      # ← "http2-" 前缀 → 强制 HTTP/2
      port: 9090
      targetPort: 9090

    - name: grpc-users      # ← "grpc-" 前缀 → gRPC (HTTP/2 + proto)
      port: 9091
      targetPort: 9091

    - name: tcp-database    # ← "tcp-" 前缀 → 纯 L4 TCP Proxy
      port: 5432
      targetPort: 5432

    - name: tcp-mysql        # ← "mysql-" 前缀 → MySQL 协议感知
      port: 3306
      targetPort: 3306

    - name: tcp-redis        # ← "redis-" 前缀 → Redis 协议感知
      port: 6379
      targetPort: 6379

    - name: tcp-mongo        # ← "mongo-" 前缀 → MongoDB 协议感知
      port: 27017
      targetPort: 27017

    - name: https-secure     # ← "https-" 前缀 → TLS 终止
      port: 443
      targetPort: 8443

    - name: tls-other        # ← "tls-" 前缀 → TLS passthrough
      port: 8443
      targetPort: 8443
```

### 2.2 前缀映射表

```
┌─────────────┬────────────────────────────┬──────────────────────────┐
│  端口名前缀   │  Envoy Filter              │  底层行为                 │
├─────────────┼────────────────────────────┼──────────────────────────┤
│  http-*     │  HTTP Connection Manager   │  HTTP/1.1 解析           │
│             │                            │  支持 HTTP/2 upgrade     │
│             │                            │  路由: method+path+header│
├─────────────┼────────────────────────────┼──────────────────────────┤
│  http2-*    │  HTTP Connection Manager   │  强制 HTTP/2 codec       │
│             │  (codec: AUTO → HTTP2)     │  不支持 HTTP/1.1 升级    │
├─────────────┼────────────────────────────┼──────────────────────────┤
│  grpc-*     │  HTTP Connection Manager   │  HTTP/2 codec            │
│             │  + gRPC Stats filter       │  gRPC 状态码追踪          │
│             │                            │  gRPC 路由 (service/method)│
├─────────────┼────────────────────────────┼──────────────────────────┤
│  tcp-*      │  TCP Proxy                 │  纯 L4 转发              │
│             │                            │  不解析任何 L7 协议       │
├─────────────┼────────────────────────────┼──────────────────────────┤
│  mysql-*    │  TCP Proxy                 │  L4 转发                 │
│             │  (+ MySQL filter 可选)      │  可选: MySQL 协议指标     │
├─────────────┼────────────────────────────┼──────────────────────────┤
│  mongo-*    │  TCP Proxy                 │  L4 转发                 │
│             │  (+ Mongo filter 可选)      │  可选: MongoDB 协议指标   │
├─────────────┼────────────────────────────┼──────────────────────────┤
│  redis-*    │  TCP Proxy                 │  L4 转发                 │
│             │  (+ Redis filter 可选)      │  可选: Redis 命令追踪     │
├─────────────┼────────────────────────────┼──────────────────────────┤
│  https-*    │  TLS Inspector             │  终止 TLS                │
│             │  + HTTP Connection Manager │  再做 L7 路由            │
├─────────────┼────────────────────────────┼──────────────────────────┤
│  tls-*      │  TCP Proxy                 │  TLS passthrough         │
│             │  (SNI-based routing)       │  不终止 TLS              │
├─────────────┼────────────────────────────┼──────────────────────────┤
│  (无前缀)    │  自动检测                   │  嗅探前几个字节判断       │
│             │                            │  默认降级为 TCP Proxy    │
└─────────────┴────────────────────────────┴──────────────────────────┘
```

---

## 三、Pilot (Istiod) 的协议推断过程

### 3.1 源码级分析

```go
// pilot/pkg/model/service.go 中的核心函数

// 从 K8s Service Port Name 推断协议
func ProtocolInstance(name string) protocol.Instance {
    // 提取 name 中 "-" 前面的部分作为前缀
    prefix := strings.SplitN(name, "-", 2)[0]

    switch prefix {
    case "http", "http2", "grpc":
        return protocol.HTTP2  // grpc 和 http2 都走 HTTP/2 codec
    case "tcp":
        return protocol.TCP
    case "https":
        return protocol.HTTPS
    case "tls":
        return protocol.TLS
    case "mongo":
        return protocol.Mongo
    case "mysql":
        return protocol.MySQL
    case "redis":
        return protocol.Redis
    case "udp":
        return protocol.UDP
    default:
        return protocol.Unsupported  // 触发自动检测
    }
}
```

### 3.2 Istiod 的 xDS 配置生成流程

```
K8s API Server
    │
    │  Watch:
    │  ├── Service (port name → 协议推断)
    │  ├── Endpoints (Pod IP 列表)
    │  ├── Pod (labels → Identity)
    │  ├── VirtualService (L7 路由规则)
    │  ├── DestinationRule (LB/熔断/mTLS)
    │  └── Gateway (入口网关配置)
    │
    ▼
Istiod (Pilot) 内部模型构建
    │
    ├── ServiceInstance: {service, port, protocol, endpoints}
    │
    ▼ xDS 配置生成
    │
    ├── LDS (Listener Discovery Service)
    │   │  为每个端口生成一个 Listener
    │   │  协议决定 Filter Chain 的类型
    │   │
    │   └── 输出:
    │       Listener {
    │         address: 0.0.0.0:<port>
    │         filter_chains: [
    │           filters: [
    │             name: "envoy.filters.network.http_connection_manager"
    │             // 或 "envoy.filters.network.tcp_proxy"
    │             // 取决于端口名前缀推断的协议
    │           ]
    │         ]
    │       }
    │
    ├── RDS (Route Discovery Service)
    │   │  只对 HTTP/gRPC Listener 生成路由配置
    │   │
    │   └── 输出:
    │       RouteConfiguration {
    │         virtual_hosts: [
    │           domains: ["my-app", "my-app.default", ...]
    │           routes: [
    │             match: {prefix: "/api/v1"} → cluster: v1
    │             match: {prefix: "/api/v2"} → cluster: v2
    │           ]
    │         ]
    │       }
    │
    ├── CDS (Cluster Discovery Service)
    │   │  为每个上游 Service 生成 Cluster
    │   │
    │   └── 输出:
    │       Cluster {
    │         name: "outbound|80||my-app.default.svc.cluster.local"
    │         type: EDS
    │         lb_policy: ROUND_ROBIN
    │         transport_socket: {  // mTLS 配置
    │           name: "envoy.transport_sockets.tls"
    │         }
    │       }
    │
    └── EDS (Endpoint Discovery Service)
        │  为每个 Cluster 提供后端 Pod IP 列表
        │
        └── 输出:
            ClusterLoadAssignment {
              endpoints: [
                {address: "10.244.1.15:8080"},
                {address: "10.244.2.20:8080"},
                {address: "10.244.3.8:8080"}
              ]
            }
```

---

## 四、Envoy 的 Listener 与 Filter Chain 深度剖析

### 4.1 Listener 配置结构

```json
{
  "listeners": [
    {
      "name": "0.0.0.0_8080",
      "address": {
        "socket_address": {
          "address": "0.0.0.0",
          "port_value": 8080
        }
      },
      "filter_chains": [
        {
          "filter_chain_match": {
            "transport_protocol": "raw_buffer",
            "application_protocols": ["http/1.1", "h2c"]
          },
          "filters": [
            {
              "name": "envoy.filters.network.http_connection_manager",
              "typed_config": {
                "@type": "type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager",
                "codec_type": "AUTO",
                "stat_prefix": "inbound_0.0.0.0_8080",
                "route_config": {
                  "virtual_hosts": [
                    {
                      "name": "inbound|http|8080",
                      "domains": ["*"],
                      "routes": [
                        {
                          "match": {"prefix": "/"},
                          "route": {"cluster": "inbound|8080||"}
                        }
                      ]
                    }
                  ]
                },
                "http_filters": [
                  {
                    "name": "envoy.filters.http.jwt_authn",
                    "typed_config": { ... }
                  },
                  {
                    "name": "envoy.filters.http.rbac",
                    "typed_config": { ... }
                  },
                  {
                    "name": "envoy.filters.http.cors",
                    "typed_config": { ... }
                  },
                  {
                    "name": "envoy.filters.http.router",
                    "typed_config": { ... }
                  }
                ]
              }
            }
          ]
        },
        {
          "filter_chain_match": {
            "transport_protocol": "raw_buffer"
          },
          "filters": [
            {
              "name": "envoy.filters.network.tcp_proxy",
              "typed_config": {
                "@type": "type.googleapis.com/envoy.extensions.filters.network.tcp_proxy.v3.TcpProxy",
                "stat_prefix": "inbound_tcp_0.0.0.0_8080",
                "cluster": "inbound|8080||"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### 4.2 Filter Chain 匹配逻辑

```
新连接到达 Listener (0.0.0.0:8080)
    │
    ▼ Envoy 开始 Filter Chain 匹配
    │
    ├── Step 1: Transport Protocol 匹配
    │   │
    │   ├── TLS Inspector Filter 运行
    │   │   │  读取 ClientHello
    │   │   │  检查是否有 TLS 记录头 (0x16 0x03)
    │   │   │
    │   │   ├── 有 TLS → transport_protocol = "tls"
    │   │   │   └── 提取 SNI (Server Name Indication)
    │   │   │       └── application_protocols 匹配 ALPN
    │   │   │           (h2, http/1.1, istio, istio-http/1.0, ...)
    │   │   │
    │   │   └── 无 TLS → transport_protocol = "raw_buffer"
    │   │       └── 进入 Step 2
    │   │
    │   └── 根据 transport_protocol 选择候选 filter chain 集合
    │
    ├── Step 2: Application Protocol 匹配 (仅 raw_buffer)
    │   │
    │   ├── 如果配置了 HTTP Inspector:
    │   │   │  读取数据流的前几个字节
    │   │   │
    │   │   ├── 检测到 "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
    │   │   │   → application_protocol = "h2c"
    │   │   │
    │   │   ├── 检测到 "GET " / "POST " / "PUT " / "HEAD " ...
    │   │   │   → application_protocol = "http/1.1"
    │   │   │
    │   │   └── 其他
    │   │       → 无法识别，使用默认 filter chain (通常是 TCP Proxy)
    │   │
    │   └── 选择匹配的 filter chain
    │
    └── Step 3: 执行匹配的 Filter Chain
        │
        ├── HTTP Connection Manager → L7 处理
        └── TCP Proxy → L4 直接转发
```

### 4.3 TLS Inspector — 内核级细节

```go
// Envoy TLS Inspector 的工作原理

// 监听 socket 设置:
setsockopt(fd, SOL_TCP, TCP_FASTOPEN, ...)
// 不建立完整 TLS 握手，只读取 ClientHello

// 读取 ClientHello 数据包:
recv(fd, buffer, max_peek_size, MSG_PEEK)
// MSG_PEEK: 窥探数据但不消费（应用层后续还能读到）

// 解析 ClientHello:
// +--------+--------+--------+--------+
// | 0x16   | 0x0301 | Length | Handshake Type (0x01 = ClientHello)
// +--------+--------+--------+--------+
// | ... SNI Extension ...              |
// | ... ALPN Extension ...             |
// +------------------------------------+

// ALPN (Application-Layer Protocol Negotiation):
// Client 发送支持的协议列表:
//   ["h2", "http/1.1"]
// Server 选择一个:
//   "h2" 或 "http/1.1"

// 这决定了:
//   h2        → HTTP/2 Connection Manager
//   http/1.1  → HTTP/1.1 Connection Manager
```

**ALPN 在 Envoy 中的角色：**

```
客户端 (带 mTLS)                    Envoy Sidecar
     │                                  │
     │──── ClientHello ────────────────▶│
     │     ALPN: [h2, http/1.1]        │
     │                                  │ TLS Inspector 解析
     │                                  │ 选择 "h2"
     │◀─── ServerHello ────────────────│
     │     ALPN: h2                     │
     │                                  │
     │     TLS 握手完成                  │
     │                                  │ Filter Chain:
     │     HTTP/2 连接                   │ → HCM (HTTP/2 codec)
     │                                  │
     │──── HEADERS frame ──────────────▶│ gRPC 路由
     │     :method = POST               │ /pb.UsersService/GetUser
     │     :path = /pb.UsersService/... │
```

---

## 五、HTTP Inspector — 无 TLS 场景的协议嗅探

### 5.1 Envoy 的 `envoy.filters.network.http_inspector`

```yaml
# Envoy 内部加载的 filter（Istio 自动配置）
filter_chains:
  - filters:
      - name: envoy.filters.network.http_inspector   # ← 先嗅探
      - name: envoy.filters.network.http_connection_manager
```

**嗅探过程：**

```
新 TCP 连接到达 (0.0.0.0:8080)
    │
    ▼ HTTP Inspector Filter 运行
    │
    │  recv(fd, peek_buf, 8, MSG_PEEK)  // 窥探前 8 字节
    │
    │  peek_buf 内容:
    │  ┌─────────────────────────────────────────────┐
    │  │ "PRI * HTTP" → HTTP/2 前言                   │
    │  │ "GET "       → HTTP/1.1 GET                  │
    │  │ "POST "      → HTTP/1.1 POST                 │
    │  │ "PUT "       → HTTP/1.1 PUT                  │
    │  │ "DELETE "    → HTTP/1.1 DELETE                │
    │  │ "HEAD "      → HTTP/1.1 HEAD                 │
    │  │ "PATCH "     → HTTP/1.1 PATCH                │
    │  │ "OPTIONS "   → HTTP/1.1 OPTIONS               │
    │  │ "CONNECT "   → HTTP/1.1 CONNECT               │
    │  │ 其他         → 非 HTTP，走 TCP Proxy            │
    │  └─────────────────────────────────────────────┘
    │
    ├── 识别为 HTTP → 设置 application protocol
    │   └── 选择 HTTP Connection Manager filter chain
    │
    └── 未识别 → 选择 TCP Proxy filter chain
```

### 5.2 内核层面的 MSG_PEEK 机制

```
用户态 (Envoy)                    内核态
     │                               │
     │  recv(fd, buf, 8, MSG_PEEK)   │
     │──────────────────────────────▶│
     │                               │  TCP Recv Buffer:
     │                               │  ┌──────────────────┐
     │                               │  │ G E T / a p i... │
     │                               │  └──────────────────┘
     │                               │         ↑
     │                               │  读取前 8 字节到 buf
     │                               │  但不移动 read pointer
     │                               │  后续 read() 还能读到
     │                               │
     │◀──────────────────────────────│  返回 8
     │                               │
     │  // Envoy 判断协议后:           │
     │  // 如果是 HTTP → 注入 HCM     │
     │  // HCM 后续的 recv() 从头读取  │
     │                               │
     │  recv(fd, buf, 4096, 0)       │
     │──────────────────────────────▶│
     │                               │  TCP Recv Buffer:
     │                               │  ┌──────────────────┐
     │                               │  │ G E T / a p i... │ ← read pointer
     │                               │  └──────────────────┘
     │                               │
     │◀──────────────────────────────│  完整数据
```

---

## 六、自动协议检测 (Istio 1.8+)

### 6.1 `ISTIO_META_AUTO_DETECTION` 配置

从 Istio 1.8 开始，如果端口名没有协议前缀，Istio 会启用自动检测：

```yaml
# Istio ConfigMap (istio-sidecar-injector)
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio
  namespace: istio-system
data:
  mesh: |
    # 自动协议检测模式
    # "STRICT"  - 严格模式，未识别的端口不创建 Listener（危险）
    # "DEFAULT" - 默认模式，未识别的端口用 auto detection
    defaultConfig:
      proxyMetadata:
        ISTIO_META_HTTP10: "1"      # 支持 HTTP/1.0
```

### 6.2 自动检测的时序

```
客户端连接到未命名端口 (e.g. port.name = "myport")
    │
    ▼
Envoy Listener 在该端口上等待
    │
    ▼ 开始嗅探 (timeout: 通常 10s)
    │
    ├── 0-10s 内收到数据
    │   │
    │   ├── 前 8 字节匹配 HTTP 前言
    │   │   → 切换到 HTTP Connection Manager
    │   │   → 后续数据按 HTTP 处理
    │   │
    │   └── 前 8 字节不匹配
    │       → 切换到 TCP Proxy
    │       → 已读取的数据透传
    │
    └── 10s 超时
        → 降级为 TCP Proxy
        → 如果有数据积压，先透传
```

**问题与风险：**

```
⚠️  自动检测的已知问题:

1. 首包延迟:
   每个新连接第一次请求有额外延迟
   (嗅探需要读取足够字节)

2. 协议误判:
   某些 TCP 协议的首字节可能恰好匹配 HTTP 方法
   例如: 某个自定义二进制协议以 0x47('G') 开头
   → 被误判为 "GET" → 走 HTTP 路由 → 失败

3. 已建立连接的切换问题:
   嗅探期间如果有多个请求快速到达
   可能丢失第一个请求的前几个字节

4. WebSocket:
   需要 HTTP 升级，自动检测能正确处理
   但如果端口名是 tcp-* → 无法走 HTTP 升级路径
   WebSocket 必须用 http-* 前缀
```

---

## 七、Envoy 的 HTTP Codec 机制

### 7.1 Codec 类型

```
┌──────────────────────────────────────────────────────┐
│  Envoy HTTP Codec 架构                                │
│                                                       │
│  HttpConnectionManager                               │
│    │                                                  │
│    ├── codec_type: AUTO                              │
│    │   └── 运行时根据实际协议自动选择                     │
│    │                                                  │
│    ├── codec_type: HTTP1                             │
│    │   └── 只接受 HTTP/1.1                            │
│    │       │  代码: source/common/http/http1/codec*.cc│
│    │       │  解析: 状态机逐字节解析请求行和头部          │
│    │       └── 支持 chunked encoding                  │
│    │                                                  │
│    ├── codec_type: HTTP2                             │
│    │   └── 只接受 HTTP/2                              │
│    │       │  代码: source/common/http/http2/codec*.cc│
│    │       │  解析: HPACK 头部压缩                     │
│    │       └── 支持流多路复用、server push              │
│    │                                                  │
│    └── codec_type: AUTO                              │
│        └── 根据连接的第一个帧自动选择                    │
│            ├── SETTINGS frame → HTTP/2                │
│            └── 文本方法行 → HTTP/1.1                   │
└──────────────────────────────────────────────────────┘
```

### 7.2 HTTP/1.1 解析器的内核交互

```
Envoy HTTP/1.1 Parser:
    │
    │  注册 read callback 到 Event Loop (libevent / libev)
    │
    ▼ 事件触发: fd 可读
    │
    │  read(fd, buffer, 16384)     // 一次读取一个 TCP 窗口
    │
    ▼ 状态机解析:
    │
    │  状态: REQUEST_LINE
    │  │  查找 \r\n
    │  │  解析: GET /api/v1/users HTTP/1.1
    │  │  提取: method=GET, path=/api/v1/users, version=1.1
    │  ▼
    │  状态: HEADERS
    │  │  逐行解析:
    │  │  Host: my-app.default.svc.cluster.local
    │  │  Content-Type: application/json
    │  │  Authorization: Bearer eyJhbG...
    │  │  x-request-id: abc-123
    │  │  (空行 \r\n 表示头部结束)
    │  ▼
    │  状态: BODY (如果有 Content-Length 或 Transfer-Encoding)
    │  │  读取请求体
    │  ▼
    │  状态: COMPLETE
    │  └── 构造 Envoy 内部 HeaderMap → 传递给 HTTP Filters
```

### 7.3 HTTP/2 帧解析

```
Envoy HTTP/2 Parser:
    │
    │  Connection Preface:
    │  "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
    │  + SETTINGS frame
    │
    ▼ 帧解析循环:
    │
    │  每个帧: 9 字节头 + payload
    │  ┌──────────┬──────────┬────┬─────┬──────────┐
    │  │ Length(3) │ Type(1)  │Flags│StreamID(4)│ Payload│
    │  └──────────┴──────────┴────┴─────┴──────────┘
    │
    │  Frame Types:
    │  ├── 0x0 DATA        → 请求/响应体
    │  ├── 0x1 HEADERS     → HPACK 压缩的头部 (替代 HTTP/1.1 的文本头部)
    │  ├── 0x2 PRIORITY    → 流优先级
    │  ├── 0x3 RST_STREAM  → 流重置
    │  ├── 0x4 SETTINGS    → 连接设置
    │  ├── 0x5 PUSH_PROMISE→ Server Push
    │  ├── 0x6 PING        → 心跳
    │  ├── 0x7 GOAWAY      → 关闭连接
    │  └── 0x8 WINDOW_UPDATE → 流控
    │
    │  HEADERS frame 解码 (HPACK):
    │  ├── 静态表查找
    │  ├── 动态表查找
    │  └── Huffman 解码
    │  → 得到: :method=POST, :path=/pb.UsersService/GetUser
    │          :authority=my-app:9090, content-type=application/grpc
    │
    └── 识别为 gRPC (当 content-type = application/grpc)
        └── 注入 gRPC Statistics Filter
```

---

## 八、Sidecar 流量拦截的完整内核路径

### 8.1 iptables 规则链

```bash
# Istio init 容器 (istio-init) 执行的规则

# ============= NAT 表 =============

# 1. PREROUTING 链 → 入站流量入口
iptables -t nat -A PREROUTING -j ISTIO_INBOUND

# 2. 入站链: 只拦截目标端口是应用端口的流量
iptables -t nat -A ISTIO_INBOUND -p tcp --dport 8080 -j ISTIO_IN_REDIRECT
iptables -t nat -A ISTIO_INBOUND -p tcp --dport 9090 -j ISTIO_IN_REDIRECT
# 其他端口 (如 15090, 15021 健康检查) 不拦截

# 3. 重定向到 Envoy 入站端口
iptables -t nat -A ISTIO_IN_REDIRECT -p tcp -j REDIRECT --to-port 15006
# 15006 = Envoy virtual inbound listener

# 4. OUTPUT 链 → 出站流量入口
iptables -t nat -A OUTPUT -j ISTIO_OUTPUT

# 5. 出站链: 排除 Envoy 自身的流量（防止死循环）
iptables -t nat -A ISTIO_OUTPUT -m owner --uid-owner 1337 -j RETURN
# 1337 = envoy 用户的 UID

iptables -t nat -A ISTIO_OUTPUT -m owner --gid-owner 1337 -j RETURN
# 1337 = envoy 用户组的 GID

# 6. 排除目标是本机的流量
iptables -t nat -A ISTIO_OUTPUT -d 127.0.0.1/32 -j RETURN

# 7. 其他出站流量全部重定向到 Envoy 出站端口
iptables -t nat -A ISTIO_OUTPUT -j ISTIO_REDIRECT
iptables -t nat -A ISTIO_REDIRECT -p tcp -j REDIRECT --to-port 15001
# 15001 = Envoy virtual outbound listener
```

### 8.2 iptables 拦截的内核数据包路径

```
┌─────────────────────────────────────────────────────────────────┐
│  应用进程 (PID in container net namespace)                       │
│                                                                  │
│  write(sockfd, http_request, len)                               │
│      │                                                           │
│      ▼                                                           │
│  TCP 发送缓冲区 → TCP 分段 → IP 包构造                           │
│      │                                                           │
│      ▼ Netfilter PREROUTING / OUTPUT                           │
│      │                                                           │
│      │  ┌──────────────────────────────────────────────────┐    │
│      │  │  NAT 表: OUTPUT 链                                │    │
│      │  │                                                    │    │
│      │  │  匹配: src = 127.0.0.1 (app 进程)                 │    │
│      │  │         dst = 10.97.42.15 (Service ClusterIP)     │    │
│      │  │         dport = 80                                │    │
│      │  │                                                    │    │
│      │  │  不匹配 owner --uid-owner 1337                    │    │
│      │  │  不匹配 -d 127.0.0.1                              │    │
│      │  │                                                    │    │
│      │  │  动作: REDIRECT --to-port 15001                   │    │
│      │  │                                                    │    │
│      │  │  内核操作:                                          │    │
│      │  │  1. 保存原始目的地址到 conntrack                    │    │
│      │  │     (SO_ORIGINAL_DST 可以查询)                     │    │
│      │  │  2. DNAT: dst → 127.0.0.1:15001                  │    │
│      │  │  3. 包重新路由到 loopback 接口                      │    │
│      │  └──────────────────────────────────────────────────┘    │
│      │                                                           │
│      ▼                                                           │
│  loopback (lo) 接口                                              │
│      │                                                           │
│      ▼                                                           │
│  Envoy 进程 (监听 127.0.0.1:15001)                              │
│      │                                                           │
│      │  getsockopt(fd, SOL_IP, SO_ORIGINAL_DST, ...)           │
│      │  → 获取原始目的地址: 10.97.42.15:80                      │
│      │                                                           │
│      │  查询: Cluster = "outbound|80||my-app.default..."       │
│      │  L7 路由匹配 → 选择后端 Pod                               │
│      │  负载均衡 → 10.244.2.20:8080                              │
│      │  mTLS 封装 (如果启用)                                     │
│      │                                                           │
│      ▼  Envoy 发出请求                                           │
│  connect(10.244.2.20:8080)                                      │
│      │                                                           │
│      ▼                                                           │
│  NAT 表: OUTPUT 链                                              │
│      │  匹配 owner --uid-owner 1337 → RETURN (放行)            │
│      │  ← Envoy 自身的出站流量不被拦截，防止死循环                 │
│      │                                                           │
│      ▼                                                           │
│  正常路由 → CNI → 目标 Pod                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 `SO_ORIGINAL_DST` 的内核实现

```c
// Envoy 中获取原始目的地址的代码:
// source/common/network/utility.cc

Address::InstanceConstSharedPtr Utility::getOriginalDst(int fd) {
    struct sockaddr_storage addr;
    socklen_t addr_len = sizeof(addr);

    // 系统调用: getsockopt
    // 内核从 conntrack 表中查找 DNAT 前的原始目的地址
    if (getsockopt(fd, SOL_IP, SO_ORIGINAL_DST,
                   &addr, &addr_len) == -1) {
        return nullptr;
    }

    // 返回: 10.97.42.15:80 (Service ClusterIP)
    return Address::InstanceConstSharedPtr(
        new Address::IpInstance(reinterpret_cast<struct sockaddr_in*>(&addr))
    );
}

// 内核中的实现:
// net/netfilter/nf_conntrack_core.c
// → nf_conntrack_get_tuplepr() → 查找 conntrack 条目
// → 返回 DNAT 前的原始 dst
```

---

## 九、Envoy Filter Chain 执行流水线

### 9.1 请求处理的完整 Filter 执行顺序

```
入站请求 (inbound):
┌──────────────────────────────────────────────────────┐
│  Network Filters (按顺序执行，双向)                    │
│                                                       │
│  1. TLS Inspector (嗅探 TLS/ALPN)                     │
│  2. HTTP Inspector (嗅探 HTTP 方法)                    │
│  3. HTTP Connection Manager (如果是 HTTP)              │
│       │                                               │
│       ├── HTTP Filter Chain (单向，请求→)               │
│       │   1. Istio AuthN Filter                        │
│       │      ├── 验证 mTLS 证书                        │
│       │      ├── 验证 JWT token                        │
│       │      └── 设置 dynamic metadata                 │
│       │                                               │
│       │   2. Istio RBAC Filter                         │
│       │      ├── 读取 AuthN 设置的 metadata             │
│       │      ├── 匹配 RBAC 规则                        │
│       │      └── ALLOW / DENY                          │
│       │                                               │
│       │   3. Istio Stats Filter                        │
│       │      ├── 记录请求指标                           │
│       │      │   ├── istio_requests_total              │
│       │      │   ├── istio_request_duration_milliseconds│
│       │      │   └── istio_request_bytes               │
│       │      └── 按 response_code 分类                 │
│       │                                               │
│       │   4. Istio Fault Injection Filter              │
│       │      ├── 注入延迟 (VirtualService.fault.delay) │
│       │      └── 注入中止 (VirtualService.fault.abort) │
│       │                                               │
│       │   5. Envoy Router Filter                       │
│       │      ├── 路由匹配 (host + path + headers)      │
│       │      ├── 选择 Cluster (负载均衡)                │
│       │      ├── 选择 Endpoint (具体的 Pod IP)          │
│       │      ├── 重试逻辑                              │
│       │      ├── 超时处理                              │
│       │      └── 转发到上游                             │
│       │                                               │
│       └── HTTP Filter Chain (反向，响应←)               │
│           5. Router Filter (收到响应)                    │
│           3. Stats Filter (记录响应指标)                 │
│           2. RBAC Filter (不执行)                       │
│           1. AuthN Filter (不执行)                      │
└──────────────────────────────────────────────────────┘
```

### 9.2 从 xDS 到 Envoy 内存的配置加载

```
Istiod 推送 xDS (gRPC stream)
    │
    ▼ Envoy xDS Client 收到
    │
    ├── LDS Response → ListenerManager
    │   │  ├── 遍历新 Listener 配置
    │   │  ├── 对每个 Listener:
    │   │  │   ├── 创建 ListenerImpl 对象
    │   │  │   ├── 创建 FilterChainManager
    │   │  │   ├── 对每个 FilterChain:
    │   │  │   │   ├── 创建 NetworkFilterChainFactory
    │   │  │   │   │   ├── HttpConnectionManagerConfig
    │   │  │   │   │   │   ├── 创建 RouteMatcher (从 RDS)
    │   │  │   │   │   │   ├── 创建 HTTP Filter Chain
    │   │  │   │   │   │   │   ├── AuthN Filter Factory
    │   │  │   │   │   │   │   ├── RBAC Filter Factory
    │   │  │   │   │   │   │   ├── Stats Filter Factory
    │   │  │   │   │   │   │   └── Router Filter Factory
    │   │  │   │   │   │   └── Codec 配置 (AUTO/HTTP1/HTTP2)
    │   │  │   │   │   └── TcpProxyConfig (备用)
    │   │  │   │   └── TLS Context (如果有)
    │   │  │   └── 注册到 socket 监听
    │   │  └── 替换旧 Listener (热重启 or drain)
    │   │
    ├── RDS Response → HttpConnectionManager
    │   │  └── 更新路由表 (RouteMatcher)
    │   │       ├── VirtualHost 查找表
    │   │       ├── Route 规则
    │   │       └── WeightedCluster 权重
    │   │
    ├── CDS Response → ClusterManager
    │   │  └── 创建/更新 Cluster 对象
    │   │       ├── LoadBalancer (ROUND_ROBIN/LEAST_CONN/RANDOM)
    │   │       ├── CircuitBreaker 配置
    │   │       ├── OutlierDetection (熔断检测)
    │   │       └── TLS 上下文
    │   │
    └── EDS Response → Cluster
        └── 更新 Endpoint 列表
            ├── health check 状态
            ├── 权重
            └── locality 信息 (zone/region)
```

---

## 十、调试与验证

### 10.1 查看 Envoy 收到的 xDS 配置

```bash
# 方法 1: Envoy Admin API
kubectl exec <pod> -c istio-proxy -- \
  curl -s localhost:15000/config_dump | jq '.configs[]'

# 方法 2: 查看特定 Listener
kubectl exec <pod> -c istio-proxy -- \
  curl -s localhost:15000/listeners | jq

# 方法 3: 查看所有 Cluster
kubectl exec <pod> -c istio-proxy -- \
  curl -s localhost:15000/clusters | jq

# 方法 4: 查看路由配置
kubectl exec <pod> -c istio-proxy -- \
  curl -s localhost:15000/routes | jq

# 方法 5: istioctl 分析工具
istioctl proxy-config listener <pod> -o json
istioctl proxy-config cluster <pod> -o json
istioctl proxy-config route <pod> -o json
istioctl proxy-config endpoint <pod> -o json
```

### 10.2 验证端口识别结果

```bash
# 查看 Listener 的 Filter Chain
istioctl proxy-config listener my-app-pod -n production --port 8080 -o json

# 输出关键字段:
# {
#   "name": "0.0.0.0_8080",
#   "filterChains": [
#     {
#       "filterChainMatch": {
#         "transportProtocol": "raw_buffer"
#       },
#       "filters": [
#         {
#           "name": "envoy.filters.network.http_connection_manager",
#           ...
#         }
#       ]
#     },
#     {
#       "filterChainMatch": {
#         "transportProtocol": "tls",
#         "applicationProtocols": ["istio", "istio-http/1.0", "istio-http/1.1", "istio-h2"]
#       },
#       "filters": [
#         {
#           "name": "envoy.filters.network.http_connection_manager",
#           ...
#         }
#       ]
#     }
#   ]
# }
```

### 10.3 实时观察协议嗅探

```bash
# 查看 Envoy 的协议嗅探统计
kubectl exec <pod> -c istio-proxy -- \
  curl -s localhost:15000/stats | grep http_inspector

# output:
# http_inspector.http10_found: 0
# http_inspector.http11_found: 156
# http_inspector.http2_found: 89
# http_inspector.no_protocol_found: 3

# 查看 TLS Inspector 统计
kubectl exec <pod> -c istio-proxy -- \
  curl -s localhost:15000/stats | grep tls_inspector

# output:
# tls_inspector.client_hello_too_large: 0
# tls_inspector.connection_closed: 0
# tls_inspector.sni_found: 245
# tls_inspector.sni_not_found: 0
# tls_inspector.tls_found: 245
# tls_inspector.tls_not_found: 12
```

### 10.4 抓包验证

```bash
# 在 Pod 内抓包（需要 NET_ADMIN 权限）
kubectl exec <pod> -c istio-proxy -- \
  tcpdump -i eth0 -nn -X port 8080 -c 5

# 看到的数据流:
# 1. 客户端 → Envoy (plaintext HTTP/1.1)
#    GET /api/users HTTP/1.1
#    Host: my-app:8080
#
# 2. Envoy → 上游 (mTLS + HTTP/2, 如果 Istio mTLS 开启)
#    TLS ClientHello
#    ALPN: istio-h2
#    HTTP/2 HEADERS frame
#    :method: GET
#    :path: /api/users
```

---

## 总结：端口识别的决策树

```
                    连接到达 Pod:PORT
                          │
                          ▼
                 ┌── 端口名有前缀? ──┐
                 │                    │
                YES                  NO
                 │                    │
                 ▼                    ▼
          ┌──────────┐        ┌───────────────┐
          │ 前缀匹配: │        │ 自动检测模式    │
          │ http-*   │→ HCM   │               │
          │ http2-*  │→ HCM   │ 1. TLS Inspector│
          │ grpc-*   │→ HCM   │   检查 TLS?    │
          │ tcp-*    │→ TCP   │       │       │
          │ mysql-*  │→ TCP   │  YES  │  NO   │
          │ mongo-*  │→ TCP   │   │   │       │
          │ redis-*  │→ TCP   │   ▼   ▼       │
          │ https-*  │→ HCM   │ ALPN  HTTP     │
          │ tls-*    │→ TCP   │ 匹配  Inspector│
          │          │        │       │       │
          └──────────┘        │  HCM  匹配?   │
                              │       │       │
                              │  YES  │  NO   │
                              │   │   │       │
                              │   ▼   ▼       │
                              │  HCM  TCP     │
                              │  Proxy        │
                              └───────────────┘
                                  │
                                  ▼
                            Filter Chain 执行
                    (AuthN → RBAC → Stats → Fault → Router)
```

**最佳实践建议：**

```yaml
# ✅ 始终使用明确的端口名前缀，不要依赖自动检测
ports:
  - name: http-api       # 明确声明 HTTP
  - name: grpc-users     # 明确声明 gRPC
  - name: tcp-database   # 明确声明 TCP

# ❌ 避免
ports:
  - name: myport         # 会触发自动检测，有延迟和误判风险
  - name: ""             # 更糟糕
  - name: 8080           # 不是有效前缀，将触发自动检测
```

有具体场景需要深入展开的，随时提问。
