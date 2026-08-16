---
title: StatefulSet 部署中间件的底层细节分析
date: 2026-09-07 14:15:00
tags:
  - Kubernetes
  - StatefulSet
  - 中间件
  - PVC
categories:
  - Kubernetes
---

## 一、为什么中间件必须用 StatefulSet？

中间件（MySQL、Redis、Kafka、Elasticsearch、ZooKeeper 等）有一个共同特征：**有状态**。Deployment 无法满足它们的需求，核心原因如下：

```
Deployment 的本质：  Pod 是"牲畜"（Cattle），坏了就杀掉重建
StatefulSet 的本质：Pod 是"宠物"（Pet），每个有唯一身份，需要被认出来
```

| 需求 | Deployment | StatefulSet |
|---|---|---|
| Pod 有稳定且唯一的网络标识 | ❌ 随机名称 | ✅ 有序命名 |
| Pod 有稳定的持久化存储 | ❌ 共享 PVC | ✅ 独立 PVC |
| 有序的部署和扩缩容 | ❌ 并行 | ✅ 按序执行 |
| 有序的滚动更新 | ❌ 并行 | ✅ 逆序更新 |
| Pod 身份在重建后保持不变 | ❌ | ✅ |

---

## 二、StatefulSet 的核心机制深度拆解

### 2.1 稳定的网络标识（Headless Service）

StatefulSet **必须**搭配一个 `clusterIP: None` 的 Headless Service：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql-headless
spec:
  clusterIP: None              # 关键：Headless
  selector:
    app: mysql
  ports:
    - port: 3306
      targetPort: 3306
  publishNotReadyAddresses: true  # 未就绪的 Pod 也会注册 DNS
```

**DNS 解析规则**：

```
Pod DNS 格式:   <pod-name>.<service-name>.<namespace>.svc.cluster.local

举例：
  mysql-0.mysql-headless.default.svc.cluster.local  → Pod IP of mysql-0
  mysql-1.mysql-headless.default.svc.cluster.local  → Pod IP of mysql-1
  mysql-2.mysql-headless.default.svc.cluster.local  → Pod IP of mysql-2

普通 Service 解析：  mysql-headless.default.svc.cluster.local → ClusterIP
Headless 解析：      mysql-headless.default.svc.cluster.local → 所有 Pod IP 列表
```

**底层实现**：
- CoreDNS 为每个 Pod 创建一条 A 记录
- 当 Pod 重建时，CoreDNS 通过 Endpoints 控制器更新记录
- Pod 的 DNS 名称是**固定的**，即使 Pod 被调度到不同节点

### 2.2 稳定的持久化存储（VolumeClaimTemplates）

这是 StatefulSet 最核心的机制之一：

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql-headless
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
        - name: mysql
          image: mysql:8.0
          volumeMounts:
            - name: mysql-data
              mountPath: /var/lib/mysql
  volumeClaimTemplates:        # 关键字段
    - metadata:
        name: mysql-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: ssd-storage
        resources:
          requests:
            storage: 50Gi
```

**VolumeClaimTemplates 的底层行为**：

```
StatefulSet 控制器创建 Pod 时：
  │
  ├──① 检查是否已存在对应的 PVC
  │     ├── 不存在 → 创建新的 PVC（等待 PV 绑定）
  │     └── 已存在 → 直接挂载（数据保留！）
  │
  ├──② PVC 命名规则：  <template-name>-<statefulset-name>-<ordinal>
  │     例如：         mysql-data-mysql-0
  │                    mysql-data-mysql-1
  │                    mysql-data-mysql-2
  │
  └──③ PVC 的生命周期独立于 Pod
        - Pod 被删除 → PVC 仍然存在
        - Pod 重建   → 挂载同一个 PVC → 数据不丢失
        - StatefulSet 缩容 → PVC 不会被自动删除（需手动处理）
```

**存储拓扑**：

```
┌─────────────────────────────────────────────────────┐
│                   StatefulSet: mysql                  │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ mysql-0  │  │ mysql-1  │  │ mysql-2  │           │
│  │          │  │          │  │          │           │
│  │ /var/lib/│  │ /var/lib/│  │ /var/lib/│           │
│  │ mysql    │  │ mysql    │  │ mysql    │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │              │                 │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐          │
│  │PVC       │  │PVC       │  │PVC       │          │
│  │mysql-data │  │mysql-data │  │mysql-data │          │
│  │-mysql-0  │  │-mysql-1  │  │-mysql-2  │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │                 │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐          │
│  │ PV (SSD) │  │ PV (SSD) │  │ PV (SSD) │          │
│  │ Node: A  │  │ Node: B  │  │ Node: C  │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
```

---

## 三、有序操作的底层实现

### 3.1 有序部署（创建）

```
StatefulSet 控制器的创建逻辑：

  for i := 0; i < replicas; i++ {
      等待 Pod[i] 进入 Running && Ready 状态
      然后再创建 Pod[i+1]
  }

实际过程：
  mysql-0: Pending → ContainerCreating → Running → Ready ✓
  mysql-1: (等待 mysql-0 Ready) → Pending → ContainerCreating → Running → Ready ✓
  mysql-2: (等待 mysql-1 Ready) → Pending → ContainerCreating → Running → Ready ✓
```

**为什么需要有序？**

对于 MySQL 主从集群：
```
mysql-0 作为 Master  必须先启动，完成初始化
mysql-1 作为 Slave   需要连接到 mysql-0 进行主从同步
mysql-2 作为 Slave   需要连接到 mysql-0 进行主从同步
```

对于 ZooKeeper / Kafka：
```
zookeeper-0 启动后开始选举
zookeeper-1 加入后重新选举
zookeeper-2 加入后形成法定人数（quorum），集群可用
```

### 3.2 有序终止（删除/缩容）

```
终止顺序与创建顺序相反：

  for i := replicas-1; i >= 0; i-- {
      先删除 Pod[i]
      等待 Pod[i] 完全终止
      再删除 Pod[i-1]
  }

实际过程：
  mysql-2: Terminating → 完全终止 ✓
  mysql-1: (等待 mysql-2 终止) → Terminating → 完全终止 ✓
  mysql-0: (等待 mysql-1 终止) → Terminating → 完全终止 ✓
```

**为什么逆序删除？**

```
Kafka 场景：
  kafka-2（Follower）  → 先删，影响最小
  kafka-1（Follower）  → 再删
  kafka-0（可能是 Controller） → 最后删，确保集群有序下线
  
MySQL 主从场景：
  Slave 先下线  → 不影响写入
  Master 最后下线  → 需要先做主从切换
```

### 3.3 Pod 管理策略

```yaml
spec:
  podManagementPolicy: OrderedReady  # 默认值，有序操作
  # podManagementPolicy: Parallel      # 并行操作（但仍保持稳定的网络标识和存储）
```

| 策略 | 创建 | 删除 | 适用场景 |
|---|---|---|---|
| `OrderedReady`（默认） | 串行，等待前一个 Ready | 逆序串行 | MySQL 主从、ZooKeeper |
| `Parallel` | 并行 | 并行 | 无主节点依赖的服务（如独立 Redis 实例） |

---

## 四、StatefulSet 更新策略的底层细节

### 4.1 RollingUpdate（默认）

```yaml
spec:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1     # 最多同时不可用的 Pod 数（默认1）
      partition: 0          # 分区更新的阈值
```

**更新顺序：逆序**（从最高 ordinal 开始）

```
假设 replicas=5，更新镜像版本 v1 → v2：

  第一步：更新 mysql-4  → 等待 Ready
  第二步：更新 mysql-3  → 等待 Ready
  第三步：更新 mysql-2  → 等待 Ready
  第四步：更新 mysql-1  → 等待 Ready
  第五步：更新 mysql-0  → 等待 Ready
```

### 4.2 分区更新（Partition）— 金丝雀发布的核心机制

```yaml
spec:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 3      # ordinal >= 3 的 Pod 会被更新
```

```
partition: 3 意味着：

  mysql-0 → 保持旧版本（v1）     ← ordinal < 3
  mysql-1 → 保持旧版本（v1）     ← ordinal < 3
  mysql-2 → 保持旧版本（v1）     ← ordinal < 3
  mysql-3 → 更新为新版本（v2）   ← ordinal >= 3
  mysql-4 → 更新为新版本（v2）   ← ordinal >= 3
```

**实际操作流程**：

```bash
# 场景：MySQL 集群升级，先更新 Slave 验证，再更新 Master

# 第一步：设置 partition=1，只更新 Slave
kubectl patch statefulset mysql -p '{"spec":{"updateStrategy":{"rollingUpdate":{"partition":1}}}}'

# 第二步：更新镜像版本
kubectl set image statefulset/mysql mysql=mysql:8.0.36

# 此时只有 mysql-1, mysql-2 被更新，mysql-0（Master）保持不变

# 第三步：验证 Slave 更新正常后，更新 Master
kubectl patch statefulset mysql -p '{"spec":{"updateStrategy":{"rollingUpdate":{"partition":0}}}}'
# 此时 mysql-0 被更新
```

### 4.3 OnDelete 更新策略

```yaml
spec:
  updateStrategy:
    type: OnDelete
```

```
行为：修改 StatefulSet 的 Pod Template 后，不会自动更新
     只有手动删除 Pod 后，重建时才会使用新的 Template

适用场景：需要完全手动控制更新节奏的中间件
```

---

## 五、常见中间件的 StatefulSet 部署

### 5.1 MySQL 主从集群

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql-headless
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      initContainers:
        # 初始化容器：根据 ordinal 决定角色
        - name: init-mysql
          image: mysql:8.0
          command:
            - bash
            - -c
            - |
              # ordinal=0 设为 Master，其余设为 Slave
              ORDINAL=${HOSTNAME##*-}
              if [ $ORDINAL -eq 0 ]; then
                echo "[mysqld]" > /mnt/conf.d/server.cnf
                echo "server-id=100" >> /mnt/conf.d/server.cnf
                echo "log-bin=mysql-bin" >> /mnt/conf.d/server.cnf
              else
                echo "[mysqld]" > /mnt/conf.d/server.cnf
                echo "server-id=$((100 + ORDINAL))" >> /mnt/conf.d/server.cnf
                echo "read-only=1" >> /mnt/conf.d/server.cnf
              fi
          volumeMounts:
            - name: conf
              mountPath: /mnt/conf.d

      containers:
        - name: mysql
          image: mysql:8.0
          ports:
            - containerPort: 3306
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: root-password
          volumeMounts:
            - name: mysql-data
              mountPath: /var/lib/mysql
            - name: conf
              mountPath: /etc/mysql/conf.d
          resources:
            requests:
              cpu: "1"
              memory: "2Gi"
            limits:
              cpu: "2"
              memory: "4Gi"

      volumes:
        - name: conf
          emptyDir: {}

  volumeClaimTemplates:
    - metadata:
        name: mysql-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: ssd-storage
        resources:
          requests:
            storage: 100Gi

  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 1   # 默认只更新 Slave，Master 手动控制
```

### 5.2 Redis Sentinel 集群

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
spec:
  serviceName: redis-headless
  replicas: 3
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7.2
          command: ["redis-server"]
          args:
            - "/conf/redis.conf"
            - "--replica-announce-ip"
            - "$(HOSTNAME).redis-headless.default.svc.cluster.local"
          env:
            - name: HOSTNAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
          ports:
            - containerPort: 6379
              name: redis
            - containerPort: 26379
              name: sentinel
          volumeMounts:
            - name: redis-data
              mountPath: /data
            - name: conf
              mountPath: /conf
          readinessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 15
            periodSeconds: 20

  volumeClaimTemplates:
    - metadata:
        name: redis-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
```

### 5.3 Kafka + ZooKeeper

```yaml
---
# ZooKeeper StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: zookeeper
spec:
  serviceName: zookeeper-headless
  replicas: 3
  selector:
    matchLabels:
      app: zookeeper
  template:
    metadata:
      labels:
        app: zookeeper
    spec:
      containers:
        - name: zookeeper
          image: zookeeper:3.9
          ports:
            - containerPort: 2181
              name: client
            - containerPort: 2888
              name: peer
            - containerPort: 3888
              name: leader-election
          env:
            # ZOO_MY_ID 由 ordinal 决定
            - name: ZOO_MY_ID
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: ZOO_SERVERS
              value: >-
                server.1=zookeeper-0.zookeeper-headless:2888:3888
                server.2=zookeeper-1.zookeeper-headless:2888:3888
                server.3=zookeeper-2.zookeeper-headless:2888:3888
          readinessProbe:
            exec:
              command: ["zkOk.sh"]
            initialDelaySeconds: 10
            periodSeconds: 10
          volumeMounts:
            - name: zk-data
              mountPath: /data
            - name: zk-datalog
              mountPath: /datalog
  volumeClaimTemplates:
    - metadata:
        name: zk-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
    - metadata:
        name: zk-datalog
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
```

---

## 六、StatefulSet 控制器的底层工作原理

### 6.1 控制循环（Control Loop）

```
┌─────────────────────────────────────────────┐
│         StatefulSet Controller               │
│                                              │
│  ┌──────────┐    watch     ┌──────────────┐ │
│  │ API Server├───────────►│ Work Queue    │ │
│  └──────────┘             └───────┬───────┘ │
│                                   │         │
│                            ┌──────▼───────┐ │
│                            │ Reconcile    │ │
│                            │ Loop         │ │
│                            └──────┬───────┘ │
│                                   │         │
│     ┌─────────────────────────────┼──────┐  │
│     │                             ▼      │  │
│     │  计算当前状态 vs 期望状态的差异      │  │
│     │                                    │  │
│     │  期望: replicas=3, image=v2        │  │
│     │  当前: 2个Pod Ready, 1个Pending    │  │
│     │                                    │  │
│     │  决策:                               │  │
│     │   - 等待 Pending Pod Ready          │  │
│     │   - 或创建缺失的 Pod                │  │
│     │   - 或删除多余的 Pod                │  │
│     └────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 6.2 StatefulSet 的 Status 字段

```yaml
status:
  replicas: 3           # 当前 Pod 总数
  readyReplicas: 3      # 就绪的 Pod 数
  currentReplicas: 2    # 当前版本的 Pod 数（更新过程中）
  updatedReplicas: 2    # 已更新的 Pod 数
  currentRevision: abc  # 当前版本的 ControllerRevision
  updateRevision: def   # 更新目标的 ControllerRevision
  collisionCount: 0     # 名称冲突计数
```

### 6.3 ControllerRevision（版本历史）

StatefulSet 使用 `ControllerRevision` 记录每一次修订：

```bash
# 查看版本历史
kubectl get controllerrevisions -l app=mysql

# 输出示例
NAME          CONTROLLER     REVISION   AGE
mysql-abc123  StatefulSet/mysql  1        2d
mysql-def456  StatefulSet/mysql  2        1h
```

支持回滚到指定版本：

```bash
kubectl rollout undo statefulset/mysql --to-revision=1
```

---

## 七、存储相关的底层细节

### 7.1 StorageClass 与动态供给

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-storage
provisioner: kubernetes.io/aws-ebs       # AWS EBS
# provisioner: pd.csi.storage.gke.io     # GCP PD
# provisioner: disk.csi.aliyun.com       # 阿里云盘
parameters:
  type: gp3
  iopsPerGB: "50"
reclaimPolicy: Retain                     # PVC 删除后保留 PV（关键！）
volumeBindingMode: WaitForFirstConsumer   # 等到 Pod 调度时才创建 PV（拓扑感知）
allowVolumeExpansion: true                # 允许扩容
```

**volumeBindingMode 的影响**：

```
Immediate（默认）：
  PVC 创建时立即绑定 PV → PV 可能在任意节点创建
  → 问题：Pod 可能被调度到与 PV 不同的节点 → 跨可用区挂载失败

WaitForFirstConsumer（推荐）：
  PVC 等待 Pod 调度后才绑定 PV → PV 创建在 Pod 所在节点/可用区
  → 保证数据局部性
```

### 7.2 PVC 保护机制（PVC Protection）

```
StatefulSet 缩容时：
  ├── Pod 被删除
  ├── PVC 仍然存在（受 finalizer 保护）
  │     └── kubernetes.io/pvc-protection finalizer
  ├── 扩容回来时，同一个 PVC 被重新挂载
  └── 数据完整保留

手动删除 PVC：
  ├── 添加 Terminating 状态
  ├── 检查是否还有 Pod 使用该 PVC
  ├── 如果有 → 等待 Pod 释放后才真正删除
  └── 如果没有 → 立即删除
```

### 7.3 PVC 的手动扩容

```bash
# 查看当前 PVC
kubectl get pvc mysql-data-mysql-0

# 在线扩容（无需重启 Pod，需要 StorageClass 支持）
kubectl patch pvc mysql-data-mysql-0 -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'

# 注意：只能扩容，不能缩容
```

---

## 八、高可用与故障恢复

### 8.1 Pod 重建后的行为

```
场景：mysql-1 所在节点宕机

  ① kubelet 检测到节点 NotReady（默认 40 秒）
  ② node-controller 开始 eviction（默认 5 分钟）
  ③ StatefulSet 控制器发现 mysql-1 不在期望状态
  ④ 调度器在健康节点上重新创建 mysql-1
  ⑤ 新的 mysql-1 挂载同一个 PVC（mysql-data-mysql-1）
  ⑥ 保留原有的数据，服务恢复

关键：Pod 名称不变 → DNS 记录自动更新 → 其他 Pod 无需修改连接地址
```

### 8.2 Pod Disruption Budget（PDB）

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: mysql-pdb
spec:
  minAvailable: 2       # 至少保证 2 个 Pod 可用
  # 或 maxUnavailable: 1
  selector:
    matchLabels:
      app: mysql
```

```
PDB 保护的场景：
  - 节点维护（kubectl drain）
  - 集群升级
  - 自动缩容

PDB 不保护的场景：
  - 节点硬件故障
  - OOM Kill
  - 手动 kubectl delete pod
```

### 8.3 优雅终止与 PreStop Hook

```yaml
containers:
  - name: mysql
    lifecycle:
      preStop:
        exec:
          command:
            - /bin/sh
            - -c
            - |
              # MySQL 优雅关闭
              mysqladmin -u root -p$MYSQL_ROOT_PASSWORD shutdown
    terminationGracePeriodSeconds: 60   # 默认 30 秒
```

```
Pod 删除时的执行顺序：
  ① 收到 SIGTERM 信号
  ② 执行 preStop Hook
  ③ Pod 状态变为 Terminating
  ④ 从 Service Endpoints 中移除（停止接收新流量）
  ⑤ 等待 terminationGracePeriodSeconds
  ⑥ 如果进程仍在运行，发送 SIGKILL 强制终止
```

---

## 九、监控与诊断

### 9.1 关键指标

```bash
# 查看 StatefulSet 状态
kubectl get statefulset mysql -o wide

# 查看每个 Pod 的详细状态
kubectl get pods -l app=mysql -o wide

# 查看 PVC 绑定状态
kubectl get pvc -l app=mysql

# 查看事件（排查调度和启动问题）
kubectl describe statefulset mysql
kubectl get events --field-selector involvedObject.name=mysql-0
```

### 9.2 常见故障排查

```bash
# 故障 1：Pod 卡在 Pending 状态
kubectl describe pod mysql-0 | grep -A 10 Events
# 常见原因：
#   - PVC 未绑定（StorageClass 问题 / 容量不足）
#   - 节点资源不足
#   - 节点亲和性不满足

# 故障 2：Pod 反复 CrashLoopBackOff
kubectl logs mysql-0 --previous     # 查看上次崩溃的日志
# 常见原因：
#   - 数据目录权限问题
#   - 存储损坏
#   - 配置文件错误

# 故障 3：有序部署卡住
kubectl get statefulset mysql
# 如果 READY 列显示 2/3，说明第 3 个 Pod 未就绪
# StatefulSet 控制器会一直等待，不会跳过

# 故障 4：PVC 处于 Lost 状态
kubectl get pvc mysql-data-mysql-1
# 原因：底层 PV 被删除或存储后端故障
```

---

## 十、总结：StatefulSet 的底层本质

```
StatefulSet = 稳定标识 + 稳定存储 + 有序操作

底层三大支柱：

1. Headless Service
   └── 提供稳定的 DNS 记录
   └── Pod 重建后 DNS 自动更新
   └── 其他组件通过域名访问，不依赖 IP

2. VolumeClaimTemplates
   └── 为每个 Pod 创建独立的 PVC
   └── PVC 生命周期独立于 Pod
   └── Pod 重建后挂载同一份数据

3. 有序控制逻辑
   └── 创建：0 → 1 → 2（前一个 Ready 才创建下一个）
   └── 删除：2 → 1 → 0（逆序）
   └── 更新：默认从最高 ordinal 开始逆序更新
   └── 分区更新：通过 partition 实现金丝雀发布
```

如果你们有具体的中间件类型、版本和部署架构，可以进一步展开具体的调优和高可用方案。
