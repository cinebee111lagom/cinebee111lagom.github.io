---
title: K8s Pod 内多镜像架构底层细节
date: 2026-09-07 13:45:00
tags:
  - Kubernetes
  - Pod
  - 容器镜像
  - Sidecar
categories:
  - Kubernetes
---

在 Kubernetes 中，一个 Pod 内运行**多个容器镜像（multiple images）** 是非常常见的架构模式。下面从多个维度进行深度分析。

---

## 一、什么场景需要一个 Pod 包含多个镜像？

在实际生产中，单一 Pod 内挂载多个镜像的典型场景：

| 场景 | 示例 |
|---|---|
| Sidecar 模式 | Envoy / Istio Proxy 作为网络代理 |
| 日志收集 | Fluentd / Filebeat 作为日志采集 Sidecar |
| 初始化容器 | `initContainers` 做前置数据拉取、数据库迁移 |
| 适配器模式 | 日志格式转换、协议适配 |
| Ambassador 模式 | 本地代理转发外部请求（如 Cloud SQL Proxy） |

---

## 二、多容器 Pod 的 YAML 定义

### 2.1 典型配置

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: adcd-multicontainer
  labels:
    app: adcd
spec:
  # 初始化容器（按顺序执行，全部成功后才启动主容器）
  initContainers:
    - name: db-migration
      image: adcd/migration:v2.3.1
      command: ["python", "manage.py", "migrate"]
      volumeMounts:
        - name: shared-data
          mountPath: /data

  # 主容器（并行运行）
  containers:
    # 容器 1：业务主服务
    - name: adcd-app
      image: adcd/app-server:v3.5.0
      ports:
        - containerPort: 8080
      resources:
        requests:
          cpu: "500m"
          memory: "512Mi"
        limits:
          cpu: "1"
          memory: "1Gi"
      imagePullPolicy: IfNotPresent
      volumeMounts:
        - name: shared-data
          mountPath: /app/data

    # 容器 2：Sidecar 日志收集
    - name: log-collector
      image: fluent/fluentd:v1.16
      resources:
        requests:
          cpu: "100m"
          memory: "128Mi"
        limits:
          cpu: "200m"
          memory: "256Mi"
      volumeMounts:
        - name: log-volume
          mountPath: /var/log/app

    # 容器 3：Sidecar 代理
    - name: envoy-proxy
      image: envoyproxy/envoy:v1.28-latest
      ports:
        - containerPort: 15001
        - containerPort: 15000

  volumes:
    - name: shared-data
      emptyDir: {}
    - name: log-volume
      emptyDir: {}

  imagePullSecrets:
    - name: adcd-registry-secret
```

---

## 三、镜像拉取的底层细节

### 3.1 Image Pull Policy（镜像拉取策略）

```yaml
imagePullPolicy: IfNotPresent   # 可选值：Always | IfNotPresent | Never
```

| 策略 | 行为 | 适用场景 |
|---|---|---|
| `Always` | 每次创建 Pod 都重新拉取 | 使用 `latest` 标签时默认 |
| `IfNotPresent` | 本地已有则不拉取 | 使用固定版本标签时推荐 |
| `Never` | 只使用本地镜像，不拉取 | 离线环境/调试 |

> **最佳实践**：始终使用明确的镜像 tag（如 `v3.5.0`），避免使用 `latest`。

### 3.2 镜像拉取流程

```
kubelet（节点级别）
  │
  ├──① 从 Pod Spec 中读取 image 字段
  │
  ├──② 检查 imagePullPolicy
  │
  ├──③ 通过 CRI（Container Runtime Interface）调用容器运行时
  │     ├── containerd → ctr / nerdctl
  │     └── CRI-O → crictl
  │
  ├──④ 容器运行时执行镜像拉取
  │     ├── 从 Registry 解析 manifest
  │     ├── 按层（layer）下载（支持并行）
  │     ├── 校验镜像摘要（digest）
  │     └── 存储到本地镜像存储
  │
  └──⑤ 创建容器并启动进程
```

### 3.3 多镜像并行拉取

kubelet 有一个参数控制镜像并行拉取数量：

```bash
# 查看 kubelet 配置
cat /var/lib/kubelet/config.yaml | grep serialize
```

```yaml
# kubelet config
serializeImagePulls: false        # 默认 false，并行拉取
maxParallelImagePulls: 5           # K8s 1.27+ 支持限制并行数
```

当 `serializeImagePulls: true` 时，多镜像会**串行拉取**，Pod 启动会明显变慢。

---

## 四、私有仓库认证（imagePullSecrets）

当 `adcd` 的镜像存储在私有仓库时，需要配置认证信息：

### 4.1 创建 Secret

```bash
kubectl create secret docker-registry adcd-registry-secret \
  --docker-server=registry.adcd.com \
  --docker-username=deploy-user \
  --docker-password=<token> \
  --docker-email=devops@adcd.com
```

### 4.2 三种挂载方式

```yaml
# 方式一：Pod 级别
spec:
  imagePullSecrets:
    - name: adcd-registry-secret

# 方式二：ServiceAccount 级别（推荐，免去每个 Pod 配置）
apiVersion: v1
kind: ServiceAccount
metadata:
  name: adcd-sa
imagePullSecrets:
  - name: adcd-registry-secret

# 方式三：准入控制器自动注入（如 Kyverno / OPA Gatekeeper）
```

---

## 五、多容器共享存储与通信

### 5.1 共享存储

同一 Pod 内的容器共享 `volumes`：

```
┌──────────────────────────────────────┐
│              Pod                      │
│                                      │
│  ┌──────────┐     ┌──────────┐      │
│  │ adcd-app │     │ log-collector│   │
│  │          │     │          │      │
│  │ /app/data├──┐  │ /var/log ├──┐   │
│  └──────────┘  │  └──────────┘  │   │
│                │                │    │
│        ┌───────┴────────────────┘   │
│        │   shared volume (emptyDir)  │
│        └────────────────────────────│
└──────────────────────────────────────┘
```

常用共享方式：

```yaml
volumes:
  # emptyDir：Pod 生命周期内的临时存储
  - name: shared-data
    emptyDir:
      medium: Memory    # 使用 tmpfs（内存盘）
      sizeLimit: 256Mi

  # ConfigMap：共享配置
  - name: config
    configMap:
      name: adcd-config

  # PVC：持久化存储
  - name: persistent-data
    persistentVolumeClaim:
      claimName: adcd-pvc
```

### 5.2 容器间通信（localhost）

同一 Pod 内的容器共享**网络命名空间**，可以通过 `localhost` 直接通信：

```
adcd-app  →  localhost:15001  →  envoy-proxy  →  外部服务
adcd-app  →  localhost:24224  →  fluentd
```

```yaml
# 容器端口映射（同一 Pod 内互相可见）
containers:
  - name: adcd-app
    # 可直接访问 localhost:15001 连接 envoy
  - name: envoy-proxy
    ports:
      - containerPort: 15001  # 对 Pod 内 localhost 可见
```

---

## 六、镜像版本管理最佳实践

### 6.1 版本标签规范

```bash
# 推荐的镜像标签格式
registry.adcd.com/adcd/app:v3.5.0          # 语义化版本
registry.adcd.com/adcd/app:v3.5.0-abc123    # 版本 + Git SHA
registry.adcd.com/adcd/app:20241215-153028   # 时间戳

# 避免使用
registry.adcd.com/adcd/app:latest           # ❌ 不确定性
registry.adcd.com/adcd/app:dev              # ❌ 模糊
```

### 6.2 镜像摘要（Digest）精确锁定

```yaml
# 使用 SHA256 摘要确保镜像不可篡改
image: registry.adcd.com/adcd/app@sha256:a1b2c3d4e5f6...
```

### 6.3 多镜像统一版本管理

```yaml
# 使用 Kustomize 的 images 字段统一管理
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
images:
  - name: adcd/app-server
    newTag: v3.5.1
  - name: adcd/migration
    newTag: v2.3.2
  - name: fluent/fluentd
    newTag: v1.16.1
```

---

## 七、多镜像的资源与调度

### 7.1 资源请求计算

Kubernetes 调度器按 **所有容器的 requests 之和** 决定调度：

```yaml
# Pod 总请求 = adcd-app + log-collector + envoy-proxy
# CPU:  500m + 100m + 100m = 700m
# Mem:  512Mi + 128Mi + 128Mi = 768Mi
```

### 7.2 Pod 开销（Pod Overhead）

Kubernetes 还会额外计算运行时开销（如 Kata Containers / gVisor）：

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
overhead:
  podFixed:
    cpu: "100m"
    memory: "160Mi"
```

---

## 八、多镜像场景的常见问题排查

### 8.1 Init 容器阻塞

```bash
# 查看 Pod 状态
kubectl get pod adcd-multicontainer -o wide

# 查看 init 容器日志
kubectl logs adcd-multicontainer -c db-migration

# 常见原因：
# - 镜像拉取失败（imagePullBackOff）
# - init 容器执行报错
# - 私有仓库认证缺失
```

### 8.2 ImagePullBackOff 排查

```bash
# 查看事件
kubectl describe pod adcd-multicontainer | grep -A 5 Events

# 典型错误信息
# Warning  Failed     Failed to pull image "adcd/app:v3.5.0": 
#   rpc error: code = NotFound desc = failed to pull and unpack image

# 排查步骤：
# 1. 镜像名称/tag 是否正确
# 2. Registry 是否可达
# 3. imagePullSecrets 是否配置
# 4. 节点上 docker/containerd 是否能登录私有仓库
```

### 8.3 多容器日志查看

```bash
# 指定容器查看日志
kubectl logs adcd-multicontainer -c adcd-app
kubectl logs adcd-multicontainer -c log-collector
kubectl logs adcd-multicontainer -c envoy-proxy

# 同时查看所有容器（K8s 1.27+）
kubectl logs adcd-multicontainer --all-containers=true

# 实时跟踪
kubectl logs -f adcd-multicontainer -c adcd-app --tail=100
```

### 8.4 镜像存储空间不足

```bash
# 查看节点磁盘使用
df -h /var/lib/containerd

# 清理未使用的镜像（containerd）
crictl rmi --prune

# 配置 kubelet 垃圾回收
# /var/lib/kubelet/config.yaml
imageGCHighThresholdPercent: 85    # 磁盘使用超过 85% 触发回收
imageGCLowThresholdPercent: 75     # 回收到 75% 以下停止
```

---

## 九、进阶：多镜像的安全扫描

```bash
# 使用 Trivy 扫描 Pod 中所有镜像
kubectl get pod adcd-multicontainer -o jsonpath='{range .spec.containers[*]}{.image}{"\n"}{end}' | \
  while read img; do
    trivy image --severity HIGH,CRITICAL "$img"
  done

# 集成准入控制（Kyverno 策略）
# 拒绝未经扫描的镜像部署
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-scan
spec:
  validationFailureAction: enforce
  rules:
    - name: check-vulnerabilities
      match:
        resources:
          kinds: ["Pod"]
      verifyImages:
        - imageReferences: ["registry.adcd.com/*"]
          attestations:
            - type: vulnerability-scan
              conditions:
                - all:
                    - key: "{{ scanner.result }}"
                      operator: Equals
                      value: "PASS"
```
