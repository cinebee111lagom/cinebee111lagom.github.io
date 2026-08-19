---
title: AI 训练基础设施存储层深度解析
date: 2026-09-08 09:00:00
tags:
  - Kubernetes
  - CSI
  - 存储
  - AI训练
categories:
  - Kubernetes
---

---

## 一、CSI（Container Storage Interface）

### 1.1 什么是 CSI

CSI 是 Kubernetes 生态中**标准化的存储插件接口**，由 Kubernetes 社区联合多家存储厂商共同制定。它的核心目标是：让任何存储系统都能以统一的方式挂载到 Pod 中，无需修改 Kubernetes 核心代码。

```
┌─────────────┐
│   kubelet    │
└──────┬──────┘
       │ gRPC（Unix Domain Socket）
       ▼
┌─────────────┐     ┌──────────────────────┐
│  CSI Driver  │────►│  后端分布式存储系统    │
│ (插件进程)    │     │  Ceph / JuiceFS / ... │
└─────────────┘     └──────────────────────┘
```

### 1.2 CSI 的三个核心组件

| 组件 | 职责 | 典型进程 |
|------|------|----------|
| **Identity Service** | 上报驱动名称、能力等元信息 | `csi-controller` |
| **Controller Service** | 创建/删除/扩容 Volume、快照 | `csi-controller` |
| **Node Service** | 在具体节点上挂载/卸载 Volume | `csi-node`（DaemonSet） |

### 1.3 工作流程

```
1. 用户创建 PVC（PersistentVolumeClaim）
        ↓
2. K8s 调度器发现 PVC 未绑定，触发 CSI Controller
        ↓
3. CSI Controller 调用后端存储 API 创建 Volume
        ↓
4. PVC 与 PV 绑定
        ↓
5. Pod 调度到某节点 → kubelet 调用该节点的 CSI Node Service
        ↓
6. CSI Node Service 执行 NodeStageVolume（格式化/mount 到全局目录）
        ↓
7. 再执行 NodePublishVolume（bind mount 到 Pod 的目标路径）
        ↓
8. 容器内看到挂载好的存储
```

---

## 二、对接主流分布式存储

### 2.1 Ceph（RBD / CephFS）

```
┌─────────────────────────────────────────────────┐
│                   Ceph 集群                      │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  MON x3  │  │  MGR x2  │  │  MDS x2  │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐             │
│  │  OSD (HDD)   │  │  OSD (SSD)   │             │
│  │  数据持久层    │  │  缓存/热数据  │             │
│  └──────────────┘  └──────────────┘             │
│                                                  │
│  接口：                                          │
│  ├── RBD（块存储）→ 训练检查点、模型快照           │
│  └── CephFS（文件系统）→ 共享训练数据集            │
└─────────────────────────────────────────────────┘
```

**Ceph RBD 的 CSI 使用示例：**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: training-checkpoint-pvc
spec:
  accessModes:
    - ReadWriteOnce        # RBD 块存储，单节点读写
  storageClassName: csi-rbd-sc
  resources:
    requests:
      storage: 500Gi
```

```yaml
# StorageClass 定义
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-rbd-sc
provisioner: rbd.csi.ceph.com
parameters:
  clusterID: <ceph-cluster-id>
  pool: training-pool
  imageFormat: "2"
  imageFeatures: layering,exclusive-lock,object-map,fast-diff
reclaimPolicy: Retain          # 训练数据重要，回收时保留
volumeBindingMode: WaitForFirstConsumer
```

**CephFS 的使用场景：**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-dataset-pvc
spec:
  accessModes:
    - ReadWriteMany            # CephFS 支持多节点同时读写
  storageClassName: csi-cephfs-sc
  resources:
    requests:
      storage: 10Ti            # 大规模训练数据集
```

**Ceph 在 AI 训练中的定位：**

| 存储类型 | 用 Ceph 什么 | 典型场景 |
|---------|-------------|---------|
| RBD | 块存储 | 检查点（checkpoint）、日志、模型权重 |
| CephFS | 共享文件系统 | 训练数据集共享读取、预处理后的中间数据 |
| 对象存储 RGW | S3 兼容接口 | 数据归档、模型制品发布 |

**注意：** Ceph 作为训练数据直接读取源时，网络 I/O 会成为瓶颈。实际场景中，通常配合本地 SSD 缓存使用。

---

### 2.2 JuiceFS

JuiceFS 是一个**云原生分布式文件系统**，其架构独特——元数据和数据分离存储：

```
┌──────────────────────────────────────────────────────┐
│                    JuiceFS 架构                        │
│                                                       │
│  ┌────────────────┐     ┌─────────────────────┐      │
│  │   元数据引擎     │     │    数据存储后端       │      │
│  │                 │     │                     │      │
│  │  Redis          │     │  S3 / MinIO / Ceph  │      │
│  │  TiKV           │     │  OSS / COS / GCS    │      │
│  │  MySQL/PG       │     │  本地磁盘            │      │
│  │  etcd           │     │                     │      │
│  └────────┬───────┘     └──────────┬──────────┘      │
│           │                        │                  │
│           ▼                        ▼                  │
│  ┌─────────────────────────────────────────┐         │
│  │         JuiceFS Client (FUSE/K8s CSI)    │         │
│  │  ┌──────────┐  ┌──────────┐             │         │
│  │  │ 元数据缓存 │  │ 数据本地缓存│             │         │
│  │  └──────────┘  └──────────┘             │         │
│  └────────────────────┬────────────────────┘         │
│                       │ POSIX 挂载                    │
│                       ▼                               │
│  ┌─────────────────────────────────────────┐         │
│  │   /jfs/training-data/  （标准目录）       │         │
│  │   /jfs/models/                         │         │
│  └─────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────┘
```

**JuiceFS 的 CSI 使用：**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: juicefs-dataset
spec:
  accessModes:
    - ReadWriteMany            # 多节点同时挂载，适合分布式训练
  storageClassName: juicefs-sc
  resources:
    requests:
      storage: 100Ti           # 容量几乎无限，取决于对象存储
```

```yaml
# StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: juicefs-sc
provisioner: csi.juicefs.com
parameters:
  csi.storage.k8s.io/provisioner-secret-name: juicefs-secret
  csi.storage.k8s.io/provisioner-secret-namespace: default
  csi.storage.k8s.io/node-publish-secret-name: juicefs-secret
  csi.storage.k8s.io/node-publish-secret-namespace: default
```

```yaml
# Secret（包含认证信息）
apiVersion: v1
kind: Secret
metadata:
  name: juicefs-secret
type: Opaque
stringData:
  name: ai-training-fs
  metaurl: redis://:password@redis:6379/0      # 元数据引擎
  storage: s3
  bucket: https://minio.internal:9000/juicefs   # 数据后端
  access-key: <ACCESS_KEY>
  secret-key: <SECRET_KEY>
  trash-days: "0"                                # 训练环境建议关闭回收站
```

**JuiceFS 在 AI 训练中的优势：**

| 特性 | 说明 |
|------|------|
| **POSIX 兼容** | 代码无需改造，`open()`/`read()`/`write()` 直接可用 |
| **多节点共享** | 多个训练 Worker 同时读同一份数据，适合 AllReduce 等分布式策略 |
| **弹性容量** | 数据存在对象存储中，容量几乎无限 |
| **本地缓存加速** | 可配置本地 SSD 作为缓存层，热数据命中本地 |
| **元数据性能** | Redis 等内存引擎处理元数据，小文件场景远优于 HDFS |

**JuiceFS vs CephFS 在 AI 训练中的对比：**

| 维度 | JuiceFS | CephFS |
|------|---------|--------|
| 元数据引擎 | 外部（Redis/TiKV 等） | 内置 MDS |
| 数据存储 | 对象存储（S3 兼容） | Ceph OSD |
| 部署复杂度 | 较低 | 较高 |
| 小文件性能 | 优秀（Redis 元数据） | 一般（MDS 瓶颈） |
| 容量扩展 | 依赖对象存储扩展 | 需扩容 OSD |
| 运维成本 | 低 | 中高 |
| 适合场景 | 海量小文件（图片/文本语料） | 需要强一致性的混合负载 |

---

## 三、本地 SSD 缓存——消除网络瓶颈的关键

### 3.1 为什么需要本地 SSD 缓存

分布式训练的数据读取模式是**高吞吐、顺序读取为主**：

```
┌─────────────────────────────────────────────────┐
│          训练数据读取的流量特征                     │
│                                                  │
│  Batch Size: 256~8192                            │
│  数据类型: 图片 224×224×3 ≈ 150KB / 张            │
│          → 单卡每秒需读 ~10,000 张 ≈ 1.5 GB/s     │
│  8 卡单节点: ~12 GB/s 持续读取                     │
│                                                  │
│  分布式存储网络带宽（典型）：                        │
│  ├── 25GbE 网卡 → 理论 3.1 GB/s                  │
│  ├── 100GbE 网卡 → 理论 12.5 GB/s               │
│  └── 实际受限于存储服务端并发能力                    │
│                                                  │
│  本地 NVMe SSD 带宽：                              │
│  ├── 单盘 → 3~7 GB/s                             │
│  └── RAID / 多盘 → 10~30 GB/s                    │
│                                                  │
│  ★ 结论：本地 SSD 比网络存储快 3~10 倍              │
└─────────────────────────────────────────────────┘
```

### 3.2 缓存架构设计

```
┌─────────────────────────────────────────────────────────┐
│                     训练 Worker 节点                       │
│                                                          │
│  ┌──────────────┐     ┌─────────────────────────────┐   │
│  │  训练框架      │     │      NVMe SSD 本地缓存        │   │
│  │  PyTorch /    │     │                             │   │
│  │  TF DataLoader│     │  /mnt/local-cache/           │   │
│  │              │     │  ├── .juicefs-cache/  ← JFS │   │
│  │  8 Worker    │     │  ├── cephfs-local-cache      │   │
│  │  进程         │     │  └── data-prefetch/         │   │
│  └──────┬───────┘     └──────────────┬──────────────┘   │
│         │                            │                   │
│         │ 1. 优先读本地               │                   │
│         │                            │                   │
│         ▼                            ▼                   │
│  ┌──────────────────────────────────────────┐            │
│  │           POSIX 读取路径                   │            │
│  │                                          │            │
│  │  命中缓存 → 直接返回（3~7 GB/s）          │            │
│  │  未命中   → 从远程存储读取 → 写入缓存      │            │
│  └──────────────────┬───────────────────────┘            │
│                     │ 网络                                 │
│                     ▼                                    │
│  ┌──────────────────────────────────────────┐            │
│  │          分布式存储集群                     │            │
│  │     Ceph / JuiceFS / NAS / 对象存储       │            │
│  └──────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

### 3.3 JuiceFS 的本地缓存配置

JuiceFS 原生支持本地缓存，是 AI 训练场景中最常用的方案之一：

```yaml
# 在 JuiceFS Mount Pod 或 CSI 配置中启用本地缓存
env:
  # 本地缓存目录
  - name: CACHE_DIR
    value: /mnt/nvme/jfs-cache        # 指向本地 NVMe SSD
    
  # 缓存大小限制（建议设为 SSD 可用空间的 80%）
  - name: CACHE_SIZE
    value: "204800"                    # 200GB，单位 MiB
    
  # 缓存过期时间
  - name: CACHE_FULL_BLOCK
    value: "true"                      # 缓存完整块而非零散部分
    
  # 预读策略
  - name: PREFETCH
    value: "1"                         # 预读 1 个块
```

**使用 hostPath 直接挂载 NVMe SSD 作为缓存：**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: training-worker
spec:
  containers:
  - name: trainer
    image: training:latest
    volumeMounts:
    - name: dataset
      mountPath: /data               # JuiceFS 挂载点
      readOnly: true
    - name: local-ssd-cache
      mountPath: /mnt/nvme/jfs-cache  # 本地缓存目录
  volumes:
  - name: dataset
    persistentVolumeClaim:
      claimName: juicefs-dataset
  - name: local-ssd-cache
    hostPath:
      path: /mnt/nvme-cache           # 宿主机 NVMe SSD 挂载路径
      type: DirectoryOrCreate
```

### 3.4 Ceph 配合本地缓存的方案

Ceph 本身没有内置的本地 SSD 缓存层用于客户端缓存，常见做法有：

**方案一：Ceph 的 BlueStore 缓存（存储端缓存）**

```
Ceph OSD 配置：
  bluestore_cache_size_ssd = 4294967296    # SSD OSD 使用 4GB 内存缓存
  bluestore_cache_size_hdd = 2147483648    # HDD OSD 使用 2GB 内存缓存
  
  # SSD 作为 HDD 的缓存层（较新版本已不推荐）
  # 推荐使用分层策略：热数据放 SSD Pool，冷数据放 HDD Pool
```

**方案二：客户端侧用 Linux dm-cache / bcache**

```bash
# 将 NVMe SSD 配置为 HDD（或网络块设备）的缓存
# 使用 bcache
make-bcache -C /dev/nvme0n1              # SSD 作为缓存设备
make-bcache -B /dev/sda                   # 网络块设备作为后端
echo /dev/nvme0n1 > /sys/block/bcache0/bcache/attach

# 透明缓存，上层应用无感知
```

**方案三：应用层预取（最常用）**

```python
import torch
from torch.utils.data import DataLoader, Dataset
import shutil
import os

class LocalCacheDataset(Dataset):
    """将远程数据预取到本地 NVMe SSD 的数据集"""
    
    def __init__(self, remote_path, local_cache_path, transform=None):
        self.remote_path = remote_path
        self.local_cache = local_cache_path
        self.transform = transform
        
        # 扫描远程目录下的所有文件
        self.file_list = sorted(os.listdir(remote_path))
        os.makedirs(local_cache_path, exist_ok=True)
    
    def _ensure_local(self, filename):
        """确保文件在本地缓存中"""
        local_path = os.path.join(self.local_cache, filename)
        if not os.path.exists(local_path):
            remote_file = os.path.join(self.remote_path, filename)
            # 先写临时文件再 rename，避免部分写入
            tmp_path = local_path + ".tmp"
            shutil.copy2(remote_file, tmp_path)
            os.rename(tmp_path, local_path)
        return local_path
    
    def __getitem__(self, idx):
        filename = self.file_list[idx]
        local_path = self._ensure_local(filename)
        data = load_and_process(local_path)   # 从本地 SSD 读取
        if self.transform:
            data = self.transform(data)
        return data
    
    def __len__(self):
        return len(self.file_list)


# 使用
dataset = LocalCacheDataset(
    remote_path="/jfs/imagenet/train",           # JuiceFS 挂载
    local_cache_path="/mnt/nvme/cache/imagenet"  # 本地 NVMe SSD
)

dataloader = DataLoader(
    dataset,
    batch_size=512,
    num_workers=8,         # 多进程并行读取
    pin_memory=True,       # 锁页内存，加速 GPU 传输
    prefetch_factor=4,     # 每个 worker 预取 4 个 batch
    persistent_workers=True
)
```

### 3.5 NVIDIA DALI——GPU 端数据预处理 + 缓存

对于图像训练，NVIDIA DALI 可以将数据加载和预处理都放到 GPU 上：

```python
from nvidia.dali import pipeline_def
import nvidia.dali.fn as fn
import nvidia.dali.types as types

@pipeline_def
def imagenet_pipeline(data_dir, shard_id, num_shards):
    # 从本地 SSD 缓存目录读取（已预取完成）
    images, labels = fn.readers.file(
        file_root=data_dir,
        shard_id=shard_id,
        num_shards=num_shards,
        random_shuffle=True,
        pad_last_batch=True,
        name="Reader"
    )
    
    # GPU 端解码和增强
    images = fn.decoders.image(images, device="mixed")     # CPU→GPU 解码
    images = fn.resize(images, device="gpu", resize_x=224, resize_y=224)
    images = fn.crop_mirror_normalize(
        images,
        device="gpu",
        dtype=types.FLOAT,
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
        mirror=fn.random.coin_flip()
    )
    
    return images, labels

# 创建 pipeline
pipe = imagenet_pipeline(
    data_dir="/mnt/nvme/cache/imagenet",   # 本地 SSD
    batch_size=256,
    num_threads=4,
    device_id=0,
    shard_id=local_rank,
    num_shards=world_size
)
pipe.build()
```

---

## 四、完整存储架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                        AI 训练存储全景                             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                   数据生命周期                            │     │
│  │                                                          │     │
│  │  原始数据          预处理数据         训练读取              │     │
│  │  (对象存储/NAS) → (分布式存储) → (本地SSD缓存) → GPU     │     │
│  │                                                          │     │
│  │  检查点/模型权重:  分布式存储 (Ceph RBD/CephFS/JuiceFS)   │     │
│  │  训练日志:         分布式存储 或 本地临时存储               │     │
│  │  最终模型:         对象存储 (S3/OSS) → 模型仓库            │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌─────────────── 存储层架构 ───────────────────────────────┐     │
│  │                                                          │     │
│  │  Tier 0: GPU HBM（显存）                                 │     │
│  │    ↓                                                     │     │
│  │  Tier 1: 主机内存（数据加载缓冲区, pinned memory）        │     │
│  │    ↓                                                     │     │
│  │  Tier 2: 本地 NVMe SSD（热数据缓存, 3~7 GB/s）           │     │
│  │    ↓                                                     │     │
│  │  Tier 3: 分布式存储（JuiceFS/CephFS, 共享数据）           │     │
│  │    ↓                                                     │     │
│  │  Tier 4: 对象存储（冷数据归档, 模型制品）                 │     │
│  │                                                          │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌─────── CSI 统一接入 ────────────────────────────────────┐     │
│  │                                                          │     │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────────┐      │     │
│  │  │ Ceph CSI │  │JuiceFS CSI│  │ 云厂商 CSI       │      │     │
│  │  │ RBD      │  │           │  │ (EBS/EFS/CFS..)  │      │     │
│  │  │ CephFS   │  │           │  │                  │      │     │
│  │  └──────────┘  └───────────┘  └──────────────────┘      │     │
│  │                                                          │     │
│  └──────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 五、关键设计原则总结

| 原则 | 说明 |
|------|------|
| **数据就近** | 训练数据尽可能贴近 GPU，本地 NVMe > 分布式存储 > 对象存储 |
| **分层缓存** | 内存 → 本地 SSD → 分布式存储 → 对象存储，逐层回退 |
| **共享读、独占写** | 训练数据集用 RWX（ReadWriteMany），检查点用 RWO（ReadWriteOnce） |
| **CSI 标准化** | 所有存储通过 CSI 接入 K8s，避免存储与调度耦合 |
| **预取 > 被动读取** | DataLoader prefetch、DALI pipeline、预热脚本，主动把数据搬到本地 |
| **弹性容量** | 对象存储做底座，容量几乎无限，按需扩展 |
| **回收策略** | 训练数据 PVC 用 `Retain`，临时缓存用 `Delete` |

存储层是 AI 训练最容易被忽视却最容易成为瓶颈的环节。**合理的分层缓存策略 + CSI 统一接入**，可以让 GPU 利用率从不足 30% 提升到 90% 以上。
