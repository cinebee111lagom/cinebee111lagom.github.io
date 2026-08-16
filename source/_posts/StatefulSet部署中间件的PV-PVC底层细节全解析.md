---
title: StatefulSet 部署中间件的 PV / PVC 底层细节全解析
date: 2026-09-07 16:45:00
tags:
  - Kubernetes
  - StatefulSet
  - PV
  - PVC
  - 中间件
categories:
  - Kubernetes
---

本文从源码级别彻底拆解 StatefulSet 如何管理 PV/PVC，以及中间件（MySQL、Redis、Kafka、Elasticsearch 等）在 StatefulSet 下的存储运作机制。

---

## 一、为什么中间件必须用 StatefulSet + PV/PVC

```
Deployment 的问题：

  Pod-0 (MySQL主) ──> PV-A    Pod 重建后 → Pod-0' ──> PV-??? (新的空卷, 数据丢失!)
  Pod-1 (MySQL从) ──> PV-B    Pod 重建后 → Pod-1' ──> PV-??? (新的空卷, 数据丢失!)

  Deployment 的 Pod 名称是随机的 (mysql-7d8f9-xk2zl)
  Pod 被调度到任意节点
  无法保证"同一个 Pod 一定绑定到同一块存储"

StatefulSet 的保证：

  mysql-0 ──> PVC data-mysql-0 ──> PV-A    重建后 → mysql-0 ──> 同一个 PVC ──> 同一个 PV-A
  mysql-1 ──> PVC data-mysql-1 ──> PV-B    重建后 → mysql-1 ──> 同一个 PVC ──> 同一个 PV-B
  mysql-2 ──> PVC data-mysql-2 ──> PV-C    重建后 → mysql-2 ──> 同一个 PVC ──> 同一个 PV-C

  Pod 名称固定且有序
  PVC 名称固定且与 Pod 绑定
  即使 Pod 被删除重建，PVC 不会重建，数据不丢失
```

---

## 二、StatefulSet PVC 底层创建机制

### 2.1 典型的中间件 StatefulSet 定义

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: middleware
spec:
  serviceName: mysql-headless      # 必须关联 Headless Service
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
          ports:
            - containerPort: 3306
          volumeMounts:
            - name: data                    # 对应 volumeClaimTemplates 的名称
              mountPath: /var/lib/mysql
            - name: conf
              mountPath: /etc/mysql/conf.d
      volumes:
        - name: conf                        # 普通 Volume（ConfigMap）
          configMap:
            name: mysql-config
  # ========== 关键部分 ==========
  volumeClaimTemplates:                     # 注意：不是 volumes
    - metadata:
        name: data                          # PVC 名称前缀
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 100Gi
```

### 2.2 volumeClaimTemplates 的 Controller 底层逻辑

**StatefulSet Controller 运行在 kube-controller-manager 内部**，其核心逻辑如下：

```
StatefulSet Controller 的核心处理流程：

func (ssc *StatefulSetController) syncStatefulSet(set *apps.StatefulSet) {

    // 1. 获取当前属于该 StatefulSet 的所有 Pod
    pods := ssc.getPodsForStatefulSet(set)

    // 2. 按 Pod 名称中的序号排序 (mysql-0, mysql-1, mysql-2, ...)
    sort.Slice(pods, func(i, j int) bool {
        return getOrdinal(pods[i]) < getOrdinal(pods[j])
    })

    // 3. 计算需要创建的下一个 Pod 序号
    replicas := int(*set.Spec.Replicas)

    // 4. 严格顺序创建（核心！）
    for ord := 0; ord < replicas; ord++ {
        // 如果 Pod 尚不存在
        if !podExists(pods, ord) {
            // 4a. 先创建该 Pod 对应的所有 PVC
            for _, pvcTemplate := range set.Spec.VolumeClaimTemplates {
                pvcName := pvcTemplate.Name + "-" + set.Name + "-" + strconv.Itoa(ord)
                // 例如: data-mysql-0, data-mysql-1

                pvc := &v1.PersistentVolumeClaim{
                    ObjectMeta: metav1.ObjectMeta{
                        Name:      pvcName,
                        Namespace: set.Namespace,
                        Labels:    set.Spec.Template.Labels,
                        OwnerReferences: []metav1.OwnerReference{{
                            APIVersion: "apps/v1",
                            Kind:       "StatefulSet",
                            Name:       set.Name,
                            UID:        set.UID,
                            Controller: boolPtr(true),
                        }},
                    },
                    Spec: pvcTemplate.Spec,   // 直接复制 PVC Spec
                }

                ssc.kubeClient.CoreV1().PersistentVolumeClaims(set.Namespace).Create(pvc)
            }

            // 4b. 然后创建 Pod
            pod := ssc.createPodForStatefulSet(set, ord)
            ssc.kubeClient.CoreV1().Pods(set.Namespace).Create(pod)

            // 4c. 等待该 Pod 变为 Running/Ready 后，才继续创建下一个
            return  // 退出 sync，等下次 reconcile
        }
    }
}
```

### 2.3 PVC 的命名规则（底层细节）

```
命名公式:  {volumeClaimTemplate.metadata.name}-{statefulset.name}-{ordinal}

volumeClaimTemplates:
  - metadata:
      name: data           ← 前缀
spec:
  ...
StatefulSet:
  name: mysql              ← StatefulSet 名称

生成的 PVC:
  data-mysql-0    →  绑定到  mysql-0
  data-mysql-1    →  绑定到  mysql-1
  data-mysql-2    →  绑定到  mysql-2

如果 volumeClaimTemplates 有多个：
  - metadata:
      name: data
  - metadata:
      name: log

生成的 PVC:
  data-mysql-0, data-mysql-1, data-mysql-2
  log-mysql-0,  log-mysql-1,  log-mysql-2
```

### 2.4 OwnerReference — PVC 生命周期绑定

```
PVC 的 OwnerReferences 指向 StatefulSet：

apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-mysql-0
  ownerReferences:
    - apiVersion: apps/v1
      kind: StatefulSet
      name: mysql
      uid: a1b2c3d4-...
      controller: true
      blockOwnerDeletion: true

这意味着：
  1. StatefulSet 被删除 → PVC 默认也会被级联删除
  2. 但 PV 的回收取决于 reclaimPolicy
     - Delete: PVC 删除 → PV 删除 → 底层卷删除（数据丢失！）
     - Retain: PVC 删除 → PV Released → 数据保留

⚠️ 生产环境中间件务必设置 reclaimPolicy: Retain！
```

---

## 三、StatefulSet Pod 与 PVC 的绑定底层细节

### 3.1 Pod 如何绑定到特定 PVC

```yaml
# StatefulSet Controller 自动为 Pod 注入 volumeClaimTemplates
# 生成的 Pod spec 中（自动生成，非用户手写）：

apiVersion: v1
kind: Pod
metadata:
  name: mysql-0
  ownerReferences:
    - apiVersion: apps/v1
      kind: StatefulSet
      name: mysql
spec:
  containers:
    - name: mysql
      volumeMounts:
        - name: data                  # 对应 volumeClaimTemplate 的 name
          mountPath: /var/lib/mysql
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: data-mysql-0       # Controller 自动填充
                                      # 与 Pod 序号对应的 PVC
```

### 3.2 Pod 删除重建时 PVC 不变的底层原因

```
时间线：
  t0: 创建 mysql-0 → 创建 PVC data-mysql-0 → 动态供给创建 PV → 绑定
  t1: mysql-0 正常运行，数据写入 PV
  t2: mysql-0 节点宕机，Pod 被删除
  t3: StatefulSet Controller 检测到 mysql-0 不存在
  t4: Controller 创建新的 mysql-0 Pod
      - 不会重新创建 PVC（因为 data-mysql-0 已存在）
      - Pod spec 中 claimName 仍然是 data-mysql-0
  t5: 新的 mysql-0 Pod 调度到某个节点
  t6: kubelet 将已有的 PV 挂载到新 Pod
  t7: mysql-0 启动，读取已有数据，无丢失

关键：StatefulSet Controller 在创建 Pod 前检查 PVC 是否已存在
func ensurePVCExists(pvcName string) {
    _, err := client.Get(pvcName)
    if err == nil {
        return  // PVC 已存在，跳过创建
    }
    // PVC 不存在，创建新的
    client.Create(newPVC(pvcName))
}
```

---

## 四、StatefulSet + PV 的调度底层细节

### 4.1 WaitForFirstConsumer 的关键作用

中间件 StatefulSet 强烈推荐使用 `volumeBindingMode: WaitForFirstConsumer`：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer   # 关键！
reclaimPolicy: Retain
parameters:
  type: gp3
```

```
为什么中间件必须用 WaitForFirstConsumer？

场景：3 节点集群，3 个可用区 (AZ-a, AZ-b, AZ-c)
      StatefulSet mysql 有 3 个副本

问题（Immediate 模式）：
  PVC data-mysql-0 创建时立即供给 → PV 在 AZ-a
  PVC data-mysql-1 创建时立即供给 → PV 在 AZ-a（同 AZ，因为当时还没调度）
  PVC data-mysql-2 创建时立即供给 → PV 在 AZ-a

  调度结果：
    mysql-0 → node-1 (AZ-a) → ✅ PV 在同 AZ
    mysql-1 → node-2 (AZ-b) → ❌ PV 在 AZ-a，跨 AZ 挂载失败！
    mysql-2 → node-3 (AZ-c) → ❌ PV 在 AZ-a，跨 AZ 挂载失败！

正确流程（WaitForFirstConsumer）：
  Step 1: PVC data-mysql-0 创建，不立即供给，Pending
  Step 2: mysql-0 Pod 创建，Scheduler 选择 node-1 (AZ-a)
  Step 3: PVC data-mysql-0 获得 annotation: selected-node=node-1
  Step 4: Provisioner 在 AZ-a 创建 PV → 绑定成功 ✅

  Step 5: PVC data-mysql-1 创建，Pending
  Step 6: mysql-1 Pod 创建，Scheduler 选择 node-2 (AZ-b)
  Step 7: PVC data-mysql-1 获得 annotation: selected-node=node-2
  Step 8: Provisioner 在 AZ-b 创建 PV → 绑定成功 ✅

  Step 9: PVC data-mysql-2 创建，Pending
  Step 10: mysql-2 Pod 创建，Scheduler 选择 node-3 (AZ-c)
  Step 11: PVC data-mysql-2 获得 annotation: selected-node=node-3
  Step 12: Provisioner 在 AZ-c 创建 PV → 绑定成功 ✅
```

### 4.2 Scheduler 的 VolumeBinding 插件

```
kube-scheduler 内部的调度流程（涉及存储部分）：

1. Filter 阶段：
   - 检查节点是否有足够 CPU/Memory
   - VolumeBinding 插件检查：
     a. PVC 的 volumeBindingMode
     b. 如果是 WaitForFirstConsumer：
        - 检查 StorageClass 对应的 Provisioner 是否支持该节点的拓扑
        - 检查 CSI NodePublishVolume 是否在该节点可用
        - 过滤掉不支持的节点

2. Score 阶段：
   - VolumeBinding 插件可能打分：
     - 优先选择已有同类型 PV 的节点（减少供给时间）
     - 优先选择拓扑分布更均匀的节点

3. Reserve 阶段：
   - 确定节点后，VolumeBinding 插件：
     - 在 PVC 上设置 annotation: volume.kubernetes.io/selected-node=<node>
     - 这触发 External Provisioner 开始创建 PV
     - 设置 scheduler 的 assume 缓存（假设绑定会成功）

4. Permit 阶段：
   - 检查 PV 是否已经创建并绑定
   - 如果未完成，Pod 进入 Waiting 状态
   - Provisioner 异步创建 PV → 绑定 → 通知 Scheduler → Pod 放行
```

### 4.3 Pod 反亲和 — 中间件高可用部署

```yaml
# 保证 MySQL 多副本分布在不同节点
spec:
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values: ["mysql"]
              topologyKey: kubernetes.io/hostname

# 更高级：跨可用区分布
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values: ["mysql"]
                topologyKey: topology.kubernetes.io/zone
```

---

## 五、常见中间件 StatefulSet 的 PV/PVC 最佳实践

### 5.1 MySQL 主从集群

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql-headless
  replicas: 3
  podManagementPolicy: OrderedReady    # 默认：严格顺序
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 0                     # 分区更新，控制升级顺序
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      terminationGracePeriodSeconds: 60  # MySQL 需要时间做 clean shutdown
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values: ["mysql"]
              topologyKey: kubernetes.io/hostname
      initContainers:
        - name: init-mysql
          image: mysql:8.0
          command:
            - bash
            - "-c"
            - |
              # 从 Pod 名称中提取序号
              ordinal=$(hostname | grep -o '[0-9]*$')
              # mysql-0 作为 primary，其余作为 replica
              if [[ $ordinal -eq 0 ]]; then
                echo "[mysqld]" > /mnt/conf.d/server-id.cnf
                echo "server-id=$((100 + $ordinal))" >> /mnt/conf.d/server-id.cnf
                echo "log-bin=mysql-bin" >> /mnt/conf.d/server-id.cnf
              else
                echo "[mysqld]" > /mnt/conf.d/server-id.cnf
                echo "server-id=$((100 + $ordinal))" >> /mnt/conf.d/server-id.cnf
                echo "read-only=1" >> /mnt/conf.d/server-id.cnf
                echo "super-read-only=1" >> /mnt/conf.d/server-id.cnf
              fi
          volumeMounts:
            - name: conf
              mountPath: /mnt/conf.d
      containers:
        - name: mysql
          image: mysql:8.0
          ports:
            - containerPort: 3306
              name: mysql
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: root-password
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
            - name: conf
              mountPath: /etc/mysql/conf.d
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
          livenessProbe:
            exec:
              command: ["mysqladmin", "ping", "-h", "localhost"]
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command: ["mysql", "-h", "localhost", "-e", "SELECT 1"]
            initialDelaySeconds: 5
            periodSeconds: 5
      volumes:
        - name: conf
          emptyDir: {}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: mysql-headless
spec:
  clusterIP: None           # Headless Service
  selector:
    app: mysql
  ports:
    - port: 3306
      name: mysql
```

**底层 DNS 解析：**

```
Headless Service: mysql-headless

DNS 记录（由 kube-dns/CoreDNS 自动生成）：
  mysql-headless.middleware.svc.cluster.local → 返回所有 Pod IP
  mysql-0.mysql-headless.middleware.svc.cluster.local → Pod-0 的 IP
  mysql-1.mysql-headless.middleware.svc.cluster.local → Pod-1 的 IP
  mysql-2.mysql-headless.middleware.svc.cluster.local → Pod-2 的 IP

这些 DNS 记录底层由 CoreDNS 的 kubernetes 插件生成：
  - Headless Service 的 endpoints 被 watch
  - 为每个 endpoint (Pod) 生成 A 记录
  - 格式: {pod-name}.{service-name}.{namespace}.svc.cluster.local
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
      initContainers:
        - name: init-redis
          image: redis:7
          command:
            - bash
            - "-c"
            - |
              ordinal=$(hostname | grep -o '[0-9]*$')
              if [[ $ordinal -eq 0 ]]; then
                # redis-0 作为 master
                cp /conf/redis-master.conf /data/redis.conf
              else
                # 其余作为 slave，指向 redis-0
                cp /conf/redis-slave.conf /data/redis.conf
                echo "replicaof redis-0.redis-headless 6379" >> /data/redis.conf
              fi
          volumeMounts:
            - name: data
              mountPath: /data
            - name: conf
              mountPath: /conf
      containers:
        - name: redis
          image: redis:7
          command: ["redis-server", "/data/redis.conf"]
          ports:
            - containerPort: 6379
              name: redis
          volumeMounts:
            - name: data
              mountPath: /data
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
      volumes:
        - name: conf
          configMap:
            name: redis-config
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 20Gi
```

### 5.3 Kafka 集群（关键：volumeClaimTemplates 多模板）

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kafka
spec:
  serviceName: kafka-headless
  replicas: 3
  selector:
    matchLabels:
      app: kafka
  template:
    metadata:
      labels:
        app: kafka
    spec:
      terminationGracePeriodSeconds: 120  # Kafka broker shutdown 较慢
      containers:
        - name: kafka
          image: confluentinc/cp-kafka:7.5.0
          ports:
            - containerPort: 9092
              name: kafka
          env:
            - name: KAFKA_BROKER_ID
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name   # 用 Pod 名称作为 broker.id
                  # 但需要是数字，通常用 initContainer 处理
            - name: KAFKA_ZOOKEEPER_CONNECT
              value: "zk-0.zk-headless:2181,zk-1.zk-headless:2181,zk-2.zk-headless:2181"
            - name: KAFKA_LOG_DIRS
              value: "/data/kafka-logs"
            - name: KAFKA_NUM_PARTITIONS
              value: "3"
            - name: KAFKA_DEFAULT_REPLICATION_FACTOR
              value: "3"
          volumeMounts:
            - name: data
              mountPath: /data
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: local-path          # Kafka 推荐 local storage
        resources:
          requests:
            storage: 200Gi

# Kafka 底层目录结构 (在 PV 上):
# /data/kafka-logs/
#   ├── __consumer_offsets-0/
#   ├── __consumer_offsets-1/
#   ├── topic-a-0/           (partition 0)
#   │   ├── 00000000000000000000.log
#   │   ├── 00000000000000000000.index
#   │   └── 00000000000000000000.timeindex
#   ├── topic-a-1/           (partition 1)
#   └── topic-a-2/           (partition 2)
```

### 5.4 Elasticsearch 集群

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
spec:
  serviceName: elasticsearch-headless
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      initContainers:
        - name: increase-vm-max-map
          image: busybox
          command: ["sysctl", "-w", "vm.max_map_count=262144"]
          securityContext:
            privileged: true
        - name: fix-permissions
          image: busybox
          command: ["sh", "-c", "chown -R 1000:1000 /usr/share/elasticsearch/data"]
          volumeMounts:
            - name: data
              mountPath: /usr/share/elasticsearch/data
      containers:
        - name: elasticsearch
          image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
          ports:
            - containerPort: 9200
              name: rest
            - containerPort: 9300
              name: inter-node
          env:
            - name: cluster.name
              value: "es-cluster"
            - name: node.name
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: discovery.seed_hosts
              value: "elasticsearch-headless"
            - name: cluster.initial_master_nodes
              value: "elasticsearch-0,elasticsearch-1,elasticsearch-2"
            - name: ES_JAVA_OPTS
              value: "-Xms2g -Xmx2g"
          volumeMounts:
            - name: data
              mountPath: /usr/share/elasticsearch/data
          resources:
            requests:
              cpu: "1"
              memory: "4Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 500Gi
```

---

## 六、StatefulSet 的 Pod 管理策略底层细节

### 6.1 OrderedReady（默认）

```
创建顺序: mysql-0 → (等待 Running) → mysql-1 → (等待 Running) → mysql-2
删除顺序: mysql-2 → (等待 Terminated) → mysql-1 → (等待 Terminated) → mysql-0
更新顺序: mysql-2 → mysql-1 → mysql-0 (逆序更新)

底层实现：
  StatefulSet Controller 的 sync 循环中：
  func getCreateOrdinal(set *apps.StatefulSet) int {
      return int(*set.Spec.Replicas) - 1  // 从 0 开始，逐个创建
  }
  func getDeleteOrdinal(set *apps.StatefulSet) int {
      // 从最大序号开始，逐个删除
      return int(*set.Spec.Replicas) - 1
  }

关键特性：
  - 如果 mysql-0 还没 Ready，mysql-1 不会被创建
  - 如果 mysql-2 挂了（CrashLoopBackOff），mysql-3 不会被创建
  - 这保证了中间件集群启动顺序的正确性（如 ZK quorum）

问题：
  - 如果 mysql-1 永远无法 Ready，整个 StatefulSet 卡住
  - 解决：手动删除 mysql-1 Pod（强制重建）
```

### 6.2 Parallel（并行模式）

```yaml
spec:
  podManagementPolicy: Parallel
```

```
创建顺序: mysql-0, mysql-1, mysql-2 同时创建
删除顺序: mysql-0, mysql-1, mysql-2 同时删除

适用场景：
  - 无状态或节点间无需特定启动顺序的中间件
  - 如 Redis Cluster（各节点独立，通过 gossip 协议自动发现）

注意：
  - PVC 仍然会同时全部创建
  - PV 供给仍然受 Provisioner 并发限制
  - 大规模部署时需注意存储系统的并发创建能力
```

---

## 七、StatefulSet 更新策略与 PV 的关系

### 7.1 RollingUpdate with Partition

```yaml
spec:
  replicas: 5
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 3     # 只更新序号 >= 3 的 Pod
```

```
更新顺序（partition=3, replicas=5）：
  序号 0, 1, 2 → 不更新，保持旧版本
  序号 4 → 更新
  序号 3 → 更新

用途：
  - 金丝雀发布：先更新 mysql-4 和 mysql-3 观察
  - 中间件滚动升级：先更新从节点，最后更新主节点

与 PV 的关系：
  - 更新 Pod 时，PVC 不会被重建
  - 新 Pod 继续使用原来的 PVC 和 PV
  - 数据不会因更新而丢失

底层实现：
  func (ssc *StatefulSetController) updateStatefulSet(set *apps.StatefulSet) {
      partition := getPartition(set)
      // 只更新 ordinal >= partition 的 Pod
      for ord := int(*set.Spec.Replicas) - 1; ord >= partition; ord-- {
          if podNeedsUpdate(pods[ord], set) {
              // 删除旧 Pod → 创建新 Pod（新镜像/新配置）
              // PVC 不动
              ssc.deletePod(pods[ord])
              // 等待删除完成后，创建新 Pod
              return
          }
      }
      // 更新 ordinal < partition 的 Pod
      for ord := partition - 1; ord >= 0; ord-- {
          // ...
      }
  }
```

---

## 八、StatefulSet PVC 的底层存储分配流程（完整链路）

```
完整链路：从 kubectl apply 到 Pod 写入数据

Step 1: kubectl apply -f mysql-sts.yaml
    │
    ▼
Step 2: API Server 存储 StatefulSet 到 etcd
    │
    ▼
Step 3: StatefulSet Controller watch 到新对象
    │
    ├── 计算需要创建 3 个 Pod (replicas: 3)
    │
Step 4: 创建 PVC data-mysql-0
    │  ┌──────────────────────────────────────────────────┐
    │  │ apiVersion: v1                                    │
    │  │ kind: PersistentVolumeClaim                       │
    │  │ metadata:                                         │
    │  │   name: data-mysql-0                              │
    │  │   namespace: middleware                           │
    │  │   ownerReferences:                                │
    │  │     - kind: StatefulSet                           │
    │  │       name: mysql                                 │
    │  │       controller: true                            │
    │  │ spec:                                             │
    │  │   storageClassName: fast-ssd                      │
    │  │   resources.requests.storage: 100Gi               │
    │  └──────────────────────────────────────────────────┘
    ▼
Step 5: PVC Controller 处理
    │
    ├── 检查是否有可用 PV → 无
    ├── 检查 StorageClass → fast-ssd 存在
    ├── volumeBindingMode=WaitForFirstConsumer → 等待调度
    ├── PVC 状态: Pending
    ▼
Step 6: 创建 Pod mysql-0
    │
    ▼
Step 7: Scheduler 调度 mysql-0
    │
    ├── Filter: 检查节点资源、拓扑约束
    ├── Score: 打分排序
    ├── Reserve: 选择 node-3 (AZ-a)
    ├── 设置 PVC annotation: selected-node=node-3
    ▼
Step 8: External Provisioner (CSI sidecar)
    │
    ├── Watch 到 PVC data-mysql-0 的 annotation 变化
    ├── 调用 CSI ControllerCreateVolume
    │   ├── capacity: 100Gi
    │   ├── parameters: {type: gp3}
    │   ├── accessibility_requirements: {zones: [AZ-a]}
    ▼
Step 9: CSI Driver 操作底层存储
    │
    ├── AWS: ec2:CreateVolume(Size=100, Type=gp3, Zone=AZ-a)
    ├── 返回: volume ID = vol-0abc1234
    ▼
Step 10: Provisioner 创建 PV 对象
    │
    ├── PV name: pvc-{pvc-uid}   (自动命名)
    ├── volumeHandle: vol-0abc1234
    ├── capacity: 100Gi
    ├── nodeAffinity: AZ-a
    ▼
Step 11: PV Controller 绑定
    │
    ├── PV.Spec.ClaimRef → data-mysql-0
    ├── PVC.Spec.VolumeName → pvc-{pvc-uid}
    ├── 两者状态均变为 Bound
    ▼
Step 12: kubelet 在 node-3 上挂载卷
    │
    ├── Attach: ec2:AttachVolume(vol-0abc1234, instance-3, /dev/xvdba)
    ├── StageVolume: mkfs.ext4 /dev/xvdba; mount → globalmount
    ├── PublishVolume: bind mount → /var/lib/kubelet/pods/{uid}/volumes/.../mount
    ▼
Step 13: MySQL 容器启动
    │
    ├── 读写 /var/lib/mysql (映射到 PV)
    ├── 数据持久化到 AWS EBS vol-0abc1234
    ▼
Step 14: StatefulSet Controller 继续创建 mysql-1, mysql-2
    (重复 Step 4 - Step 13)
```

---

## 九、底层调试与故障排查

```bash
# ===== 查看 StatefulSet 的 PVC 创建状态 =====

# 查看 StatefulSet 状态
kubectl get sts mysql -n middleware -o wide
# NAME    READY   AGE   CONTINUOS
# mysql   3/3     2d

# 查看关联的 PVC
kubectl get pvc -n middleware -l app=mysql
# NAME              STATUS   VOLUME                 CAPACITY   STORAGECLASS
# data-mysql-0      Bound    pvc-aaa-111            100Gi      fast-ssd
# data-mysql-1      Bound    pvc-bbb-222            100Gi      fast-ssd
# data-mysql-2      Bound    pvc-ccc-333            100Gi      fast-ssd

# 查看 PVC 的 ownerReferences（确认归属）
kubectl get pvc data-mysql-0 -n middleware -o jsonpath='{.metadata.ownerReferences}'
# [{"apiVersion":"apps/v1","kind":"StatefulSet","name":"mysql","uid":"xxx","controller":true}]

# ===== 查看 PV 的 nodeAffinity =====

kubectl get pv pvc-aaa-111 -o jsonpath='{.spec.nodeAffinity}'
# {"required":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"topology.kubernetes.io/zone",
#   "operator":"In","values":["ap-southeast-1a"]}]}]}}

# ===== 节点级别调试 =====

# 查看节点上的块设备
lsblk | grep xvd
# xvdba   202:16   0  100G  0 disk /var/lib/kubelet/plugins/.../globalmount

# 查看挂载点
findmnt -t ext4,xfs | grep kubelet

# 查看 kubelet 日志中的卷挂载错误
journalctl -u kubelet | grep -i "volume\|mount\|csi" | tail -50

# ===== 常见问题诊断 =====

# 问题1: StatefulSet 卡在 1/3 Ready
kubectl describe pod mysql-1 -n middleware
# 查看 Events：可能是 PVC 未 Bound

# 问题2: PVC 一直 Pending
kubectl describe pvc data-mysql-1 -n middleware
# Events:
#   Warning  ProvisioningFailed  ...  insufficient capacity in zone ap-southeast-1a
# → 原因：存储配额不足或该 AZ 无可用资源

# 问题3: Pod 删除后新 Pod 挂载失败
kubectl get volumeattachments | grep mysql
# 查看是否有残留的 VolumeAttachment 阻止新 attach
# 解决：kubectl delete volumeattachment <stuck-attachment>

# 问题4: PVC 被意外删除（ownerReferences 导致）
# 如果 StatefulSet 被删除，PVC 默认也会被删除
# 保护措施：在删除 StatefulSet 前，先移除 PVC 的 ownerReference
kubectl patch pvc data-mysql-0 -n middleware \
  -p '{"metadata":{"ownerReferences":null}}'
```

---

## 十、生产环境关键注意事项

### 10.1 存储类选择

```
中间件类型        推荐 StorageClass        说明
─────────────────────────────────────────────────────────
MySQL            gp3 / io2 (AWS)         需要稳定的 IOPS
                 pd-ssd (GCP)            推荐 provisioned IOPS
                 managed-premium (Azure)

Redis            gp3 (AWS)               内存数据库，磁盘主要用于 AOF/RDB
                 local-path              如果能接受节点绑定

Kafka            local-path / 本地 NVMe   极高吞吐，跨 AZ 延迟不可接受
                 gp3 (退而求其次)           需要高 throughput 配置

Elasticsearch    gp3 (AWS)               需要大容量 + 高 IOPS
                 pd-ssd (GCP)

ZooKeeper        local-path / 低延迟 SSD   ZK 对延迟极度敏感
                 io2 (AWS)               provisioned IOPS
```

### 10.2 回收策略与数据保护

```yaml
# 永远不要对生产中间件使用 Delete 回收策略
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd-retain
provisioner: ebs.csi.aws.com
reclaimPolicy: Retain          # 必须！
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:..."
```

### 10.3 扩容注意事项

```
PV 扩容流程（以 MySQL 为例）：

1. 修改 PVC 容量：
   kubectl edit pvc data-mysql-0 -n middleware
   # 将 storage: 100Gi 改为 storage: 200Gi

2. Expand Controller 检测到变更，调用 CSI ControllerExpandVolume

3. 底层存储系统扩展卷（如 AWS EBS 扩容，无需停机）

4. PV 的 capacity 更新为 200Gi

5. kubelet 调用 CSI NodeExpandVolume 扩展文件系统
   - ext4: resize2fs /dev/xvdba
   - xfs: xfs_growfs /var/lib/mysql
   - 这一步在 Pod 运行时执行，无需重启

⚠️ 注意：
   - 卷只能扩大，不能缩小
   - 某些存储类型扩容时可能需要短暂 I/O 停顿
   - AWS EBS 扩容后 6 小时内不能再次扩容（I/O 优化限制）
```

---

以上就是 StatefulSet 部署中间件时 PV/PVC 的完整底层细节。如果你有具体的中间件部署问题、存储性能调优需求或故障排查场景，可以直接贴出相关信息，我会给出针对性的分析和解决方案。
