---
title: 推理 Pod 底层细节 — 深度解析
date: 2026-09-07 10:45:00
tags:
  - Kubernetes
  - 推理
  - GPU
  - vLLM
categories:
  - Kubernetes
---

# Inference Pod Underlying Details — Deep Dive

# 推理 Pod 底层细节 — 深度解析

---

## 1. What Is an Inference Pod?

An **inference pod** is a Kubernetes pod specifically deployed to serve machine learning model predictions in production. Unlike training pods, inference pods are optimized for **low latency, high throughput, and resource efficiency**.

**推理 Pod** 是专门为在生产环境中提供机器学习模型预测服务而部署的 Kubernetes Pod。与训练 Pod 不同，推理 Pod 针对**低延迟、高吞吐和资源效率**进行了优化。

---

## 2. Pod Lifecycle & Scheduling

### 2.1 Scheduling Process

When you apply a Deployment or Pod manifest, the following happens:

当你应用一个 Deployment 或 Pod 清单时，会发生以下过程：

```
1. API Server receives the Pod spec
   API Server 接收 Pod 规格

2. Scheduler assigns the Pod to a Node based on:
   调度器根据以下条件将 Pod 分配到节点：
   - Resource requests (CPU, memory, GPU)
     资源请求（CPU、内存、GPU）
   - Node affinity / anti-affinity rules
     节点亲和性 / 反亲和性规则
   - Topology spread constraints
     拓扑分布约束
   - Taints and tolerations
     污点和容忍

3. Kubelet on the target node creates the Pod sandbox
   目标节点上的 Kubelet 创建 Pod 沙箱

4. Container runtime (containerd/CRI-O) pulls images and starts containers
   容器运行时（containerd/CRI-O）拉取镜像并启动容器
```

### 2.2 Example Pod Spec for Inference

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference-pod
  labels:
    app: llm-inference
    model: llama-70b
spec:
  # --- GPU Node Scheduling ---
  # --- GPU 节点调度 ---
  nodeSelector:
    accelerator: nvidia-a100
  tolerations:
    - key: "nvidia.com/gpu"
      operator: "Exists"
      effect: "NoSchedule"

  # --- Resource Requests/Limits ---
  # --- 资源请求/限制 ---
  containers:
    - name: vllm-server
      image: vllm/vllm-openai:latest
      resources:
        requests:
          memory: "48Gi"
          cpu: "8"
          nvidia.com/gpu: "2"
        limits:
          memory: "64Gi"
          cpu: "16"
          nvidia.com/gpu: "2"

      # --- Container Ports ---
      # --- 容器端口 ---
      ports:
        - containerPort: 8000
          name: http-api
          protocol: TCP

      # --- Health Probes ---
      # --- 健康探针 ---
      readinessProbe:
        httpGet:
          path: /health
          port: 8000
        initialDelaySeconds: 120
        periodSeconds: 10
      livenessProbe:
        httpGet:
          path: /health
          port: 8000
        initialDelaySeconds: 180
        periodSeconds: 30

      # --- Environment Variables ---
      # --- 环境变量 ---
      env:
        - name: MODEL_NAME
          value: "/models/llama-70b-chat"
        - name: TENSOR_PARALLEL_SIZE
          value: "2"
        - name: MAX_MODEL_LEN
          value: "8192"
        - name: GPU_MEMORY_UTILIZATION
          value: "0.90"

      # --- Volume Mounts ---
      # --- 卷挂载 ---
      volumeMounts:
        - name: model-storage
          mountPath: /models
          readOnly: true
        - name: shm
          mountPath: /dev/shm

  volumes:
    - name: model-storage
      persistentVolumeClaim:
        claimName: model-pvc-a100
    - name: shm
      emptyDir:
        medium: Memory
        sizeLimit: "8Gi"
```

---

## 3. Networking Details (Network Engineer Focus)

### 3.1 Pod Network Model

Every pod gets its own **network namespace**. Inside this namespace:

每个 Pod 都拥有自己的**网络命名空间**。在该命名空间内部：

```
┌─────────────────────────────────────────────┐
│                  Pod (Network Namespace)     │
│                                             │
│  ┌──────────┐    ┌──────────────────────┐   │
│  │ Inference│    │   Envoy/Istio Sidecar│   │
│  │ Server   │───▶│   Proxy (optional)   │   │
│  │ :8000    │    │   :15001 (inbound)   │   │
│  └──────────┘    └──────────────────────┘   │
│         │                                   │
│    eth0 (veth pair)                          │
│    10.244.1.5                                │
└────────┼────────────────────────────────────┘
         │
    veth pair (virtual ethernet)
         │
┌────────┼────────────────────────────────────┐
│  Node Network Namespace                      │
│         │                                    │
│    vethXXXXX                                 │
│         │                                    │
│    cbr0 (bridge) ── kube-proxy / CNI plugin  │
│    10.244.1.1                                │
│         │                                    │
│    eth0 (physical NIC)                       │
│    192.168.1.10                              │
└──────────────────────────────────────────────┘
```

### 3.2 CNI Plugin Internals

The **Container Network Interface (CNI)** is responsible for:

**容器网络接口（CNI）**负责以下工作：

```
1. IPAM (IP Address Management)
   - Assigns a unique IP from the pod CIDR to each pod
     从 Pod CIDR 为每个 Pod 分配唯一 IP
   - Common plugins: host-local, calico-ipam, aws-vpc-cni

2. Veth Pair Creation
   - Creates a veth pair: one end inside pod NS, one end on node bridge
     创建 veth 对：一端在 Pod 网络命名空间内，另一端在节点网桥上

3. Route Configuration
   - Pod default route → bridge → node routing table → external network
     Pod 默认路由 → 网桥 → 节点路由表 → 外部网络

4. Network Policy Enforcement
   - Calico/Cilium enforces ingress/egress rules at the eBPF or iptables level
     Calico/Cilium 在 eBPF 或 iptables 层面强制执行入站/出站规则
```

### 3.3 Service & Load Balancing for Inference Pods

```yaml
---
apiVersion: v1
kind: Service
metadata:
  name: llm-inference-svc
spec:
  selector:
    app: llm-inference
  ports:
    - name: http
      port: 80
      targetPort: 8000
      protocol: TCP
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: llm-inference-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  rules:
    - host: inference.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: llm-inference-svc
                port:
                  number: 80
```

**Traffic Flow / 流量路径：**

```
Client Request
      │
      ▼
[Load Balancer / Ingress Controller]
      │
      ▼  iptables (kube-proxy) or eBPF (Cilium)
[Service ClusterIP: 10.96.0.50:80]
      │
      ├──▶ Pod 1 (10.244.1.5:8000)   ─ weight-based
      ├──▶ Pod 2 (10.244.2.8:8000)   ─ round-robin
      └──▶ Pod 3 (10.244.3.12:8000)  ─ least-conn (if Cilium)
```

### 3.4 kube-proxy vs eBPF (Cilium)

| Aspect / 方面 | kube-proxy (iptables) | Cilium (eBPF) |
|---|---|---|
| Packet Processing / 包处理 | iptables chains, O(n) rules | eBPF programs in kernel, O(1) lookup |
| Latency / 延迟 | Higher with many services | Lower, especially at scale |
| Connection Tracking / 连接跟踪 | conntrack module | eBPF-native conntrack |
| DSR (Direct Server Return) | Not supported | Supported |
| Best for / 最佳场景 | Small clusters / 小型集群 | Large-scale inference clusters / 大规模推理集群 |

---

## 4. GPU Access from Inside the Pod

### 4.1 NVIDIA Device Plugin Architecture

```
┌─────────────────────────────────────────────────────┐
│  Node                                                │
│                                                      │
│  ┌──────────────────────┐                            │
│  │ nvidia-device-plugin │ (DaemonSet)                │
│  │ Registers with       │                            │
│  │ kubelet via gRPC     │                            │
│  └────────┬─────────────┘                            │
│           │ advertises: nvidia.com/gpu = 4           │
│           ▼                                          │
│  ┌──────────────────────┐                            │
│  │ kubelet              │                            │
│  │ Allocates GPU devices│                            │
│  │ to containers via    │                            │
│  │ Container Runtime    │                            │
│  └────────┬─────────────┘                            │
│           │                                          │
│           ▼                                          │
│  ┌──────────────────────┐                            │
│  │ containerd + NVIDIA   │                            │
│  │ Container Runtime    │                            │
│  │ Hooks               │                            │
│  │                     │                            │
│  │ Mounts:             │                            │
│  │  /dev/nvidia0        │                            │
│  │  /dev/nvidia1        │                            │
│  │  /dev/nvidiactl      │                            │
│  │  /usr/lib/x86_64-    │                            │
│  │   linux-gnu/libnvidia│                            │
│  │   -ml.so.535.129    │                            │
│  │  /usr/lib/x86_64-    │                            │
│  │   linux-gnu/libcuda  │                            │
│  │   .so.535.129        │                            │
│  └──────────────────────┘                            │
└─────────────────────────────────────────────────────┘
```

### 4.2 Inside the Container — What Happens

```bash
# Inside the inference container:
# 在推理容器内部：

# 1. NVIDIA driver is mounted from host (not installed in container)
#    NVIDIA 驱动从宿主机挂载（不安装在容器中）

# 2. Container sees GPUs as devices
#    容器将 GPU 视为设备
$ ls /dev/nvidia*
/dev/nvidia0  /dev/nvidia1  /dev/nvidiactl  /dev/nvidia-uvm  /dev/nvidia-uvm-tools

# 3. CUDA libraries are bind-mounted
#    CUDA 库通过绑定挂载
$ ls -la /usr/lib/x86_64-linux-gnu/libcuda.so*
/usr/lib/x86_64-linux-gnu/libcuda.so -> libcuda.so.535
/usr/lib/x86_64-linux-gnu/libcuda.so.535 -> libcuda.so.535.129.03

# 4. nvidia-smi works normally
#    nvidia-smi 正常工作
$ nvidia-smi
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.129.03   Driver Version: 535.129.03   CUDA Version: 12.2     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
|===============================+======================+======================|
|   0  NVIDIA A100-SXM4-80GB   | 00000000:CA:00.0 Off |                    0 |
|   1  NVIDIA A100-SXM4-80GB   | 00000000:CB:00.0 Off |                    0 |
+-------------------------------+----------------------+----------------------+
```

---

## 5. Shared Memory (/dev/shm) — Critical for Multi-GPU Inference

For **tensor parallelism** across multiple GPUs, frameworks like vLLM and NCCL use **shared memory** for inter-GPU communication:

对于跨多个 GPU 的**张量并行**，vLLM 和 NCCL 等框架使用**共享内存**进行 GPU 间通信：

```
Pod with 2 GPUs:
┌─────────────────────────────────────────┐
│                                         │
│  /dev/shm (8Gi emptyDir, medium: Memory)│
│  ┌───────────────────────────────────┐  │
│  │ NCCL shared buffers               │  │
│  │ Tensor shard communication        │  │
│  │ KV-cache metadata                 │  │
│  └───────────────────────────────────┘  │
│         │              │                │
│    GPU 0 (PCIe/NVLink)  GPU 1          │
│    Model Layer 0-39     Layer 40-79     │
│    KV Cache Part A      KV Cache Part B │
└─────────────────────────────────────────┘
```

**Why /dev/shm matters:**
默认 Docker 容器的 `/dev/shm` 只有 64MB，对于多 GPU 推理会不够用，导致 NCCL 初始化失败。这就是为什么需要显式挂载一个大的 `emptyDir` with `medium: Memory`。

---

## 6. Model Loading & Memory Layout

### 6.1 When the Pod Starts

```
Timeline of an inference pod startup:
推理 Pod 启动时间线：

t=0s     Container starts, entrypoint runs
         容器启动，入口命令运行

t=2s     vLLM initializes, detects GPUs
         vLLM 初始化，检测 GPU

t=5s     Model weights loading begins from PVC → CPU RAM → GPU VRAM
         模型权重从 PVC → CPU RAM → GPU VRAM 开始加载
         (or direct GPU memory mapping via mmap)
         （或通过 mmap 直接映射到 GPU 内存）

t=30-120s  Weights distributed across GPUs (tensor parallel)
           权重分布到多个 GPU（张量并行）

t=120s   KV cache allocated on GPU memory
         KV 缓存在 GPU 内存上分配

t=130s   CUDA graphs compiled (optional, for performance)
         CUDA 图编译（可选，用于提升性能）

t=140s   HTTP server binds to port 8000
         HTTP 服务器绑定到端口 8000

t=141s   Readiness probe passes → Pod marked Ready
         就绪探针通过 → Pod 标记为 Ready
```

### 6.2 GPU Memory Breakdown (e.g., A100 80GB)

```
┌─────────────────────────────────────────────┐
│         GPU 0 VRAM (80 GB)                  │
│                                             │
│  ┌────────────────────┐  35 GB  Model Weights (FP16, 70B model / TP=2)
│  │ Model Weights      │  模型权重（FP16，70B 模型 / 张量并行=2）
│  └────────────────────┘
│  ┌────────────────────┐  30 GB  KV Cache (dynamic, grows with seq length)
│  │ KV Cache           │  KV 缓存（动态，随序列长度增长）
│  └────────────────────┘
│  ┌────────────────────┐   5 GB  Activation memory
│  │ Activations        │  激活内存
│  └────────────────────┘
│  ┌────────────────────┐   5 GB  CUDA context + framework overhead
│  │ CUDA Context       │  CUDA 上下文 + 框架开销
│  └────────────────────┘
│  ┌────────────────────┐   5 GB  Fragmentation buffer
│  │ Buffer/Fragment    │  缓冲/碎片
│  └────────────────────┘
└─────────────────────────────────────────────┘
```

---

## 7. Request Flow Through the Inference Pod

```
HTTP Request (POST /v1/completions)
    │
    ▼
┌──────────────────────────┐
│  TCP Socket (:8000)       │
│  HTTP Server (uvicorn)    │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Tokenizer               │
│  text → token IDs        │
│  "Hello" → [15496]       │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Scheduler               │
│  (Continuous batching)   │
│  Places request into     │
│  active batch or queue   │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Model Execution         │
│  (CUDA kernel launch)    │
│                          │
│  Prefill phase:          │  ← Process all input tokens in parallel
│  Process all input tokens│     并行处理所有输入 token
│                          │
│  Decode phase:           │  ← Generate one token at a time
│  Generate one token/iter │     每次迭代生成一个 token
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Detokenizer             │
│  token IDs → text        │
│  [15496] → "Hello"       │
└────────┬─────────────────┘
         │
         ▼
HTTP Response (SSE stream or JSON)
```

---

## 8. Networking Optimization for Inference

### 8.1 Pod-to-Pod Communication (Multi-Node Tensor Parallelism)

For models too large for a single node, you need **multi-node inference**:

对于单个节点放不下的模型，需要**多节点推理**：

```
Node A (Pod 1)                    Node B (Pod 2)
┌─────────────────┐               ┌─────────────────┐
│ GPU 0 + GPU 1   │  ← RDMA/NCCL →│ GPU 2 + GPU 3   │
│ Layer 0-19      │    InfiniBand  │ Layer 20-39     │
│                 │    or RoCE v2  │                 │
│ 100 Gbps IB HCA │               │ 100 Gbps IB HCA │
└─────────────────┘               └─────────────────┘
```

**Network Requirements / 网络要求：**
- InfiniBand (200-400 Gbps) or RoCE v2 for GPU-to-GPU communication
- NCCL uses RDMA when available, falling back to TCP
- Kubernetes **does not** manage this — it requires host-level RDMA driver + device plugin

### 8.2 Network Policies for Security

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: inference-pod-policy
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
              app: api-gateway
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              purpose: model-registry
      ports:
        - protocol: TCP
          port: 443
    - to:  # Allow DNS / 允许 DNS
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
```

---

## 9. Monitoring & Observability at the Pod Level

```
┌─────────────────────────────────────────────┐
│  Inference Pod                               │
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │ App Metrics │  │ Node Exporter        │  │
│  │ /metrics    │  │ (sidecar or DS)      │  │
│  │             │  │                      │  │
│  │ - latency   │  │ - GPU temp/util/mem  │  │
│  │ - throughput│  │ - Network bandwidth  │  │
│  │ - queue len │  │ - CPU/memory usage   │  │
│  │ - tokens/s  │  │ - Disk I/O           │  │
│  └──────┬──────┘  └──────────┬───────────┘  │
│         │                    │               │
└─────────┼────────────────────┼───────────────┘
          │                    │
          ▼                    ▼
   ┌─────────────────────────────────┐
   │        Prometheus               │
   │   (scrape interval: 15s)        │
   └──────────────┬──────────────────┘
                  │
                  ▼
   ┌─────────────────────────────────┐
   │        Grafana Dashboard        │
   │   - Request latency p50/p95/p99 │
   │   - GPU memory utilization      │
   │   - Active request count        │
   │   - Token generation speed      │
   └─────────────────────────────────┘
```

**Key Metrics / 关键指标：**

| Metric / 指标 | Meaning / 含义 | Critical Threshold / 临界阈值 |
|---|---|---|
| `gpu_utilization` | GPU compute usage / GPU 计算使用率 | > 95% means saturated / 饱和 |
| `gpu_memory_used_bytes` | VRAM usage / 显存使用 | > 90% risks OOM / 有 OOM 风险 |
| `inference_request_latency_seconds` | End-to-end latency / 端到端延迟 | Depends on SLA / 取决于 SLA |
| `tokens_generated_per_second` | Throughput / 吞吐量 | Model-dependent / 取决于模型 |
| `pending_requests` | Queue depth / 队列深度 | Growing = capacity issue / 增长 = 容量问题 |

---

## 10. Failure Modes & Recovery

```
Failure Mode                          Recovery Action
失败模式                               恢复操作
─────────────────────────────────────────────────────────
OOM Killed (GPU)                      Restart pod, reduce batch size
GPU 内存不足被杀死                      重启 Pod，减小批处理大小

CUDA Error                            Restart pod, check driver version
CUDA 错误                              重启 Pod，检查驱动版本

Network timeout (model download)      Retry with exponential backoff
网络超时（模型下载）                     指数退避重试

Readiness probe failure               Pod removed from Service endpoints
就绪探针失败                            Pod 从 Service 端点中移除

Liveness probe failure                Kubelet restarts container
存活探针失败                            Kubelet 重启容器

Node failure                          Pod rescheduled to healthy node
节点故障                                Pod 重新调度到健康节点

OOM (CPU RAM)                         Pod evicted, higher memory request needed
CPU 内存不足                            Pod 被驱逐，需要提高内存请求
```

---

## Summary / 总结

An inference pod is far more than just a container running a model. At the infrastructure level, it involves:

推理 Pod 远不止是一个运行模型的容器。在基础设施层面，它涉及：

1. **Scheduling** — GPU-aware scheduling with node affinity and tolerations
   **调度** — 具有节点亲和性和容忍的 GPU 感知调度

2. **Networking** — CNI plugin manages pod IP, veth pairs, and routing; Service provides stable endpoint and load balancing
   **网络** — CNI 插件管理 Pod IP、veth 对和路由；Service 提供稳定端点和负载均衡

3. **GPU Access** — NVIDIA device plugin + container runtime hooks expose GPU devices into the container
   **GPU 访问** — NVIDIA 设备插件 + 容器运行时钩子将 GPU 设备暴露到容器中

4. **Memory Management** — Model weights + KV cache + activations must fit within GPU VRAM; /dev/shm must be sized for multi-GPU communication
   **内存管理** — 模型权重 + KV 缓存 + 激活必须适配 GPU 显存；/dev/shm 必须为多 GPU 通信分配足够大小

5. **Performance** — Continuous batching, CUDA graphs, tensor parallelism, and RDMA networking for multi-node setups
   **性能** — 连续批处理、CUDA 图、张量并行以及多节点设置的 RDMA 网络

6. **Observability** — Prometheus metrics + Grafana dashboards for latency, throughput, GPU utilization, and queue depth monitoring
   **可观测性** — Prometheus 指标 + Grafana 仪表板监控延迟、吞吐量、GPU 利用率和队列深度
