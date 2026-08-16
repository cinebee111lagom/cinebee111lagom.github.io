---
title: Kubernetes PV / PVC 底层细节全解析
date: 2026-09-07 16:00:00
tags:
  - Kubernetes
  - PV
  - PVC
  - 存储
categories:
  - Kubernetes
---

作为一名 K8s 管理员，我来从源码级别和控制面流程彻底拆解 PV 和 PVC 的底层运作机制。

---

## 一、PV 与 PVC 的本质定义

很多人把 PV 和 PVC 理解为"存储"，但它们本质上只是 **Kubernetes API 对象**，是对底层存储的**元数据描述**。

```yaml
# PV — 集群管理员提供的存储资源（供给侧）
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-data-01
  labels:
    type: ssd
spec:
  capacity:
    storage: 50Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: fast-ssd
  csi:
    driver: ebs.csi.aws.com
    volumeHandle: vol-0abc1234def56789    # 底层存储的真实 ID
    fsType: ext4
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: topology.kubernetes.io/zone
              operator: In
              values:
                - ap-southeast-1a
```

```yaml
# PVC — 用户侧的存储需求声明（消费侧）
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-data-01
  namespace: production
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: fast-ssd
  selector:
    matchLabels:
      type: ssd     # 可选：进一步筛选特定 PV
```

**关键认知：PV 是集群级别的资源（无 namespace），PVC 是 namespace 级别的资源。** 这意味着 PVC 只能在自己的 namespace 内绑定 PV，不存在跨 namespace 绑定的可能。

---

## 二、PV 与 PVC 的生命周期状态机

### 2.1 PV 的完整状态流转

```
                  ┌──────────────────────────────┐
                  │                              │
                  ▼                              │
            ┌──────────┐    绑定成功    ┌─────────┴──┐
  创建 ──>  │ Available │ ───────────>  │   Bound    │
            └──────────┘               └─────────┬──┘
                                      PVC 被删除   │
                                                  ▼
                                          ┌──────────────┐
                              reclaimPolicy 决定命运     │
                                          │              │
                               ┌──────────┼──────────┐   │
                               ▼          ▼          ▼   │
                           ┌──────┐  ┌────────┐  ┌──────┐│
                           │Delete│  │ Retain │  │Failed││
                           └──────┘  └────┬───┘  └──────┘│
                                  管理员手动 │             │
                                  清理或删除 │             │
                                          ▼             │
                                    ┌──────────┐        │
                                    │Available │ ───────┘
                                    └──────────┘  (可选：重新变为 Available)
```

### 2.2 PVC 的完整状态流转

```
  创建 ──> Pending ──> Bound ──> Lost (PV 被意外删除)
              │          │
              │          └── 正常使用中
              │
              └── 等待匹配的 PV 出现
                  (动态供给时等待 Provisioner 创建)
```

**Lost 状态的底层含义：** PVC 的 `volumeName` 字段指向的 PV 在 etcd 中已不存在，但 PVC 本身未被删除。这通常意味着有人手动删除了 PV，属于异常操作。

---

## 三、绑定（Binding）的底层实现

### 3.1 控制器架构

绑定逻辑运行在 **kube-controller-manager** 内部的 **PersistentVolume Controller（PV Controller）** 中。

```
kube-controller-manager
    │
    ├── PV Controller
    │   ├── syncVolume()   ← 监听 PV 事件（Add/Update/Delete）
    │   ├── syncClaim()    ← 监听 PVC 事件（Add/Update/Delete）
    │   └── sync()         ← 核心绑定逻辑
    │
    ├── Expand Controller  ← 处理 PVC 扩容
    │
    └── Attach/Detach Controller  ← 处理卷的节点挂载/卸载
```

### 3.2 绑定算法的核心流程

```
PV Controller 的 syncClaim() 触发条件：
    PVC 创建 / PVC 更新 / 有新 PV 变为 Available

绑定算法（简化伪代码）：

func syncClaim(pvc *v1.PersistentVolumeClaim) {
    // 1. 如果 PVC 已经 Bound，检查 PV 是否仍然存在
    if pvc.Status.Phase == Bound {
        pv := findPV(pvc.Spec.VolumeName)
        if pv == nil {
            pvc.Status.Phase = Lost    // PV 不存在，标记 Lost
        }
        return
    }

    // 2. PVC 处于 Pending，尝试找到匹配的 PV
    pvList := listAllAvailablePVs()

    // 3. 筛选逻辑（按优先级排序）
    candidates := filterPVs(pvList, pvc)
    // 匹配条件：
    //   a. PV 状态 == Available
    //   b. PV.Spec.StorageClassName == PVC.Spec.StorageClassName
    //   c. PV.Spec.Capacity >= PVC.Spec.Resources.Requests.Storage
    //   d. PV.Spec.AccessModes 包含 PVC.Spec.AccessModes
    //   e. PV.Spec.VolumeMode == PVC.Spec.VolumeMode
    //   f. PVC.Spec.Selector 匹配 PV.Labels（如果有）
    //   g. PV.Spec.NodeAffinity 与当前绑定兼容

    // 4. 从候选中选择最优 PV
    bestPV := chooseBestMatch(candidates, pvc)
    // 选择策略：
    //   - 最小容量匹配（最小满足需求的 PV 优先）
    //   - 如果容量相同，按创建时间排序

    // 5. 执行绑定
    if bestPV != nil {
        bindVolumeToClaim(bestPV, pvc)
    }
}

func bindVolumeToClaim(pv *v1.PersistentVolume, pvc *v1.PersistentVolumeClaim) {
    // 使用乐观锁（ResourceVersion）防止并发冲突
    pv.Status.Phase = Bound
    pv.Spec.ClaimRef = &v1.ObjectReference{
        Namespace: pvc.Namespace,
        Name:      pvc.Name,
        UID:       pvc.UID,
    }

    pvc.Status.Phase = Bound
    pvc.Spec.VolumeName = pv.Name

    // 先更新 PV，再更新 PVC（两个独立的 API 调用）
    apiServer.UpdatePV(pv)
    apiServer.UpdatePVC(pvc)
}
```

### 3.3 ClaimRef — 绑定的"锁"

ClaimRef 是 PV 绑定机制中最关键的底层字段：

```yaml
# 绑定后的 PV
spec:
  claimRef:
    apiVersion: v1
    kind: PersistentVolumeClaim
    name: pvc-data-01
    namespace: production
    uid: a1b2c3d4-e5f6-7890-abcd-ef1234567890
    resourceVersion: "12345"
```

**ClaimRef 的作用：**

```
1. 单向锁定：PV 通过 ClaimRef 指向 PVC，表明"我已被占用"
2. 保护机制：ClaimRef 不为空的 PV 不会被其他 PVC 抢占
3. 删除保护：如果 PV 已绑定，无法直接删除 PV（需要先删除 PVC）
4. 回收触发：PVC 删除后，PV Controller 检查 ClaimRef 决定回收行为
```

### 3.4 绑定的并发安全

PV Controller 使用了精细的并发控制：

```
问题场景：两个 PVC 同时竞争同一个 PV

PVC-A  ──读取 PV (resourceVersion=100)──> 准备绑定
PVC-B  ──读取 PV (resourceVersion=100)──> 准备绑定

解决机制：
    PVC-A 的 UpdatePV 请求携带 resourceVersion=100
    → API Server 接受，PV 变为 resourceVersion=101

    PVC-B 的 UpdatePV 请求仍携带 resourceVersion=100
    → API Server 拒绝（409 Conflict）

    PVC-B 重新获取 PV (resourceVersion=101)
    → 发现 ClaimRef 已指向 PVC-A
    → 放弃绑定，重新搜索其他 PV
```

---

## 四、动态供给（Dynamic Provisioning）的底层细节

当 StorageClass 配合 PVC 使用时，会触发动态供给：

```
完整调用链：

PVC (storageClassName: fast-ssd, phase: Pending)
    │
    ▼
PV Controller
    │  发现没有可用 PV 匹配
    │  检查 StorageClass 是否存在
    │  如果 volumeBindingMode=WaitForFirstConsumer，等待调度
    ▼
External Provisioner (CSI sidecar)
    │  Watch 到新 PVC 且 annotation 中有
    │  "volume.kubernetes.io/storage-provisioner: ebs.csi.aws.com"
    │
    │  检查是否需要处理：
    │  - PVC 未绑定
    │  - storageClassName 不为空
    │  - 等待 annotation 中有 selected-node（WaitForFirstConsumer）
    │
    │  调用 CSI ControllerCreateVolume gRPC
    ▼
CSI Controller Service (运行在 CSI Controller Pod 中)
    │
    │  操作底层存储 API：
    │  - AWS: ec2:CreateVolume → 创建 EBS 卷
    │  - Ceph: librbd create → 创建 RBD image
    │  - NFS: mkdir → 创建子目录
    ▼
返回 VolumeHandle (底层存储唯一标识)
    │
    ▼
External Provisioner 创建 PV 对象
    │
    │  apiVersion: v1
    │  kind: PersistentVolume
    │  spec:
    │    csi:
    │      driver: ebs.csi.aws.com
    │      volumeHandle: vol-0abc1234def56789
    │    capacity:
    │      storage: 50Gi
    ▼
PV Controller 执行绑定 (PV ↔ PVC)
    │
    ▼
PV 与 PVC 均变为 Bound 状态
```

### 4.1 CSI 驱动的部署架构

```
CSI Controller Pod (Deployment, 通常 2 副本)
    │
    ├── csi-provisioner (sidecar)
    │   └── 监听 PVC 事件，调用 CreateVolume/DeleteVolume
    │
    ├── csi-attacher (sidecar)
    │   └── 监听 VolumeAttachment 事件，调用 ControllerPublish/Unpublish
    │
    ├── csi-resizer (sidecar)
    │   └── 监听 PVC 扩容事件，调用 ControllerExpandVolume
    │
    ├── csi-snapshotter (sidecar)
    │   └── 监听 VolumeSnapshot 事件，调用 CreateSnapshot/DeleteSnapshot
    │
    └── ebs-csi-plugin (主容器)
        └── 实现 CSI Controller Service 的 gRPC 接口

CSI Node DaemonSet (每个节点一个 Pod)
    │
    ├── node-driver-registrar (sidecar)
    │   └── 向 kubelet 注册 CSI driver
    │
    └── ebs-csi-plugin (主容器)
        └── 实现 CSI Node Service 的 gRPC 接口
            - NodeStageVolume: 将卷格式化并挂载到 staging 目录
            - NodePublishVolume: 从 staging 目录 bind-mount 到 Pod 目录
            - NodeUnpublishVolume: 反向操作
            - NodeUnstageVolume: 反向操作
```

---

## 五、Pod 使用 PV 的挂载底层细节

当一个使用 PVC 的 Pod 被调度到某个节点时，kubelet 负责实际的卷挂载：

```
kubelet 启动 Pod 流程中的存储部分：

1. Volume Manager (在 kubelet 内) 检查 Pod 需要的卷
   │
   ├── 读取 PVC → 找到绑定的 PV → 获取 CSI driver 信息
   │
2. 确保卷已 Attach 到节点 (调用 CSI ControllerPublishVolume)
   │
   │  这一步由 AttachDetachController (kube-controller-manager) 或
   │  kubelet 自身完成，取决于配置
   │
   │  ControllerPublishVolume 请求：
   │    volumeId: "vol-0abc1234def56789"
   │    nodeId: "i-0node1234"
   │    volumeCapability: { accessMode: SINGLE_NODE_WRITER, mount: { fsType: ext4 } }
   │
   │  底层操作：
   │    AWS: ec2:AttachVolume(vol-xxx, instance-xxx, /dev/xvdba)
   │    结果：卷出现在节点的 /dev/xvdba
   │
3. NodeStageVolume (格式化 + 挂载到全局 staging 路径)
   │
   │  CSI Node Plugin 操作：
   │    a. 检查是否需要格式化（首次使用）
   │       mkfs.ext4 /dev/xvdba
   │    b. 创建 staging 目录
   │       mkdir -p /var/lib/kubelet/plugins/kubernetes.io/csi/.../globalmount
   │    c. 挂载
   │       mount /dev/xvdba /var/lib/kubelet/plugins/kubernetes.io/csi/.../globalmount
   │
4. NodePublishVolume (从 staging 路径 bind-mount 到 Pod 路径)
   │
   │  CSI Node Plugin 操作：
   │    a. 创建 Pod 级别的挂载目录
   │       mkdir -p /var/lib/kubelet/pods/{pod-uid}/volumes/kubernetes.io~csi/{pv-name}/mount
   │    b. Bind mount
   │       mount --bind .../globalmount .../pods/{pod-uid}/volumes/.../mount
   │
5. kubelet 在容器创建时将挂载路径映射到容器内
   │
   │  container.volumeMounts:
   │    - name: data
   │      mountPath: /var/lib/app   ← 容器内路径
   │      # 实际映射到节点上的 .../pods/{pod-uid}/volumes/.../mount
   │
   ▼
Pod 容器启动，正常读写 /var/lib/app
```

### 5.1 节点上的实际目录结构

```bash
# 在节点上查看实际挂载情况
$ tree /var/lib/kubelet/plugins/kubernetes.io/csi/
├── ebs.csi.aws.com/
│   └── {volume-handle}/
│       └── globalmount          # Stage 目录（全局共享）
│           └── [实际数据]

$ tree /var/lib/kubelet/pods/
├── {pod-uid}/
│   └── volumes/
│       └── kubernetes.io~csi/
│           └── {pv-name}/
│               └── mount         # Publish 目录（Pod 专用）
│                   └── [实际数据]

# globalmount 和 mount 通过 bind mount 关联
# 多个 Pod 使用同一个 PV (ReadWriteMany) 时：
#   - globalmount 只有一个（StageVolume 只执行一次）
#   - mount 有多个（每个 Pod 一个，都 bind mount 到同一个 globalmount）
```

---

## 六、PV/PVC 删除的底层细节

### 6.1 正常删除流程

```
用户执行: kubectl delete pvc my-pvc

1. API Server 标记 PVC 为 DeletionTimestamp (软删除)

2. PVC Finalizer: kubernetes.io/pvc-protection
   → 等待所有使用该 PVC 的 Pod 终止
   → Pod 全部删除后，移除 Finalizer

3. PVC 被彻底删除

4. PV Controller 检测到 PVC 删除
   │
   ├── reclaimPolicy = Delete:
   │   ├── 调用 CSI DeleteVolume
   │   │   └── 底层操作：AWS ec2:DeleteVolume / Ceph rbd rm / ...
   │   ├── 删除 PV 的 Finalizer: external-provisioner-volume-deletion
   │   ├── 删除 PV 对象
   │   └── 结果：PV 和底层卷都不存在了
   │
   └── reclaimPolicy = Retain:
       ├── PV 状态变为 Released
       ├── ClaimRef 仍然保留（指向已删除的 PVC）
       ├── 底层卷保留不动
       └── 管理员需要手动处理：
           kubectl delete pv my-pv              # 删除 PV 对象
           # 或
           kubectl patch pv my-pv -p '{"spec":{"claimRef":null}}'
           # 清除 ClaimRef，PV 重新变为 Available
```

### 6.2 Finalizer 保护机制

```yaml
# PV 上的 Finalizers
metadata:
  finalizers:
    - kubernetes.io/pv-protection       # 防止 PV 被意外删除
    - external-provisioner-volume-deletion  # 动态供给时，删除 PV 前先删底层卷

# PVC 上的 Finalizers
metadata:
  finalizers:
    - kubernetes.io/pvc-protection      # 防止 PVC 被意外删除（Pod 还在用时）
```

**pv-protection 的工作原理：**

```
场景：有人尝试 kubectl delete pv my-pv，但该 PV 已绑定到 PVC

1. API Server 设置 DeletionTimestamp
2. PV Controller 检测到 PV 被标记删除
3. 检查 PV.Status.Phase == Bound
4. 拒绝删除 → PV 继续存在
5. 只有 PVC 先被删除，PV 变为 Released/Retained
6. 此时才能真正删除 PV
```

---

## 七、挂载模式（Access Modes）的底层真相

```yaml
accessModes:
  - ReadWriteOnce      # RWO: 单节点读写
  - ReadOnlyMany       # ROX: 多节点只读
  - ReadWriteMany      # RWX: 多节点读写
  - ReadWriteOncePod   # RWOP: 单 Pod 读写 (K8s 1.27+ GA)
```

**底层真相：Access Modes 只是元数据标注，不被 kubelet 强制执行。**

```
实际的读写约束由底层存储系统保证：

AWS EBS:
  - 支持 RWO（一个卷只能 attach 到一个实例）
  - 不支持 RWX（EBS 不允许同时 attach）

NFS:
  - 支持 RWO / ROX / RWX
  - NFS Server 负责并发控制

CephFS:
  - 支持 RWO / ROX / RWX
  - Ceph 的分布式锁机制保证一致性

Ceph RBD:
  - 支持 RWO（单个 image 只能 map 到一个节点）
  - RWX 需要 CephFS 而非 RBD
```

**如果你在 PV 上标注 `ReadWriteMany` 但底层存储不支持多节点写入，不会有任何报错——只有实际使用时才会出现数据损坏。** 这是很多新手踩的坑。

---

## 八、Block Mode vs Filesystem Mode

```yaml
# 默认：Filesystem 模式
volumeMode: Filesystem
# kubelet 会格式化卷，挂载为目录，Pod 看到的是目录

# Block 模式
volumeMode: Block
# 卷以原始块设备形式暴露给 Pod，不做格式化
# Pod 看到的是 /dev/xxx 设备文件
```

**底层差异：**

```
Filesystem 模式挂载链：
  底层卷 → mkfs → mount → bind mount → Pod 容器目录
  容器内访问: /data/myfile (普通文件系统路径)

Block 模式挂载链：
  底层卷 → 直接暴露设备节点 → bind mount → Pod 容器设备路径
  容器内访问: /dev/xvdba (原始块设备)

用途：
  - 数据库 (如 PostgreSQL) 可能想直接管理文件系统 → Block Mode
  - 高性能场景减少一层文件系统开销 → Block Mode
  - 普通应用 → Filesystem Mode（绝大多数场景）
```

---

## 九、高级调试命令速查

```bash
# ===== PV 相关 =====

# 查看所有 PV 及其状态
kubectl get pv -o wide

# 查看 PV 详细信息（特别是 ClaimRef、nodeAffinity、事件）
kubectl describe pv <pv-name>

# 查看 PV 的完整 YAML（包括所有底层字段）
kubectl get pv <pv-name> -o yaml

# 查看哪些 PV 未绑定
kubectl get pv --field-selector=status.phase=Available

# 强制释放一个 stuck 的 PV（清除 ClaimRef，谨慎操作）
kubectl patch pv <pv-name> -p '{"spec":{"claimRef":null}}'

# ===== PVC 相关 =====

# 查看所有 PVC
kubectl get pvc --all-namespaces

# 查看 PVC 绑定状态
kubectl get pvc <pvc-name> -o jsonpath='{.status.phase}'

# 查看 PVC 绑定到了哪个 PV
kubectl get pvc <pvc-name> -o jsonpath='{.spec.volumeName}'

# ===== 节点级别排查 =====

# 查看节点上挂载的 CSI 卷
lsblk  # 查看块设备

# 查看 kubelet 的卷目录
ls /var/lib/kubelet/pods/<pod-uid>/volumes/

# 查看 VolumeAttachment 对象（记录哪些卷 attach 到了哪些节点）
kubectl get volumeattachments
kubectl describe volumeattachment <name>

# 查看 CSI 驱动注册状态
kubectl get csinodes -o yaml

# ===== 事件排查 =====

# 查看 PV/PVC 相关事件
kubectl get events --field-selector involvedObject.kind=PersistentVolume
kubectl get events --field-selector involvedObject.kind=PersistentVolumeClaim

# 查看 CSI provisioner 日志
kubectl logs -n kube-system -l app=csi-provisioner --tail=100
```

---

## 十、常见底层问题与解决方案

| 问题 | 底层原因 | 解决方案 |
|------|----------|----------|
| PVC 一直 Pending | 无匹配 PV / StorageClass 不存在 / Provisioner 未运行 | `kubectl describe pvc` 查看 Events |
| PV Bound 但 Pod 启动失败 | 卷无法 attach 到节点 / AZ 不匹配 | 检查 VolumeAttachment 和 CSI Node 日志 |
| 删除 PV 卡住 | Finalizer 阻塞 / 底层卷删除失败 | 手动移除 Finalizer（最后手段）|
| PVC 扩容不生效 | allowVolumeExpansion 未开启 / CSI 不支持 | 检查 SC 配置和 CSI 版本 |
| 多 Pod 挂同一 PV 出错 | RWO 模式下不允许多节点挂载 | 改用 RWX 存储（NFS/CephFS）|
| Pod 迁移后卷挂载失败 | 旧的 VolumeAttachment 未清理 | 手动删除 VolumeAttachment |

---

以上就是 PV/PVC 从 API 对象层面到实际节点挂载的完整底层细节。如果你有具体的报错信息或场景需要排查，可以直接贴出来，我会结合这些底层机制给出针对性的诊断方案。
