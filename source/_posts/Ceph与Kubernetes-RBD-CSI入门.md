---
title: Ceph 与 Kubernetes RBD CSI 入门
date: 2026-08-30 12:15:00
tags:
  - Ceph
  - Kubernetes
  - 入门
categories:
  - Ceph 新手入门
---

**Ceph CSI** 让 K8s 通过 PVC 动态使用 Ceph RBD/CephFS 存储。

## 架构

```
Pod → PVC → CSI Provisioner → Ceph RBD 镜像
                    ↓
              ceph.conf + cephx
```

## 安装（ceph-csi 概念）

```bash
# 创建 CSI 专用 pool
ceph osd pool create kubernetes 128
ceph osd pool application enable kubernetes rbd

# 创建 client 用户（权限最小化）
ceph auth get-or-create client.kubernetes mon 'profile rbd' osd 'profile rbd pool=kubernetes' mgr 'allow rw'
```

Helm 安装 ceph-csi-rbd chart，配置 clusterID、monitors、pool、userKey。

## StorageClass 示例

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-rbd
provisioner: rbd.csi.ceph.com
parameters:
  clusterID: <fsid>
  pool: kubernetes
  csi.storage.k8s.io/provisioner-secret-name: csi-rbd-secret
  csi.storage.k8s.io/provisioner-secret-namespace: ceph-csi
reclaimPolicy: Delete
allowVolumeExpansion: true
```

## 测试 PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: ceph-rbd
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
    - name: app
      image: nginx
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: test-pvc
```

## RBD vs CephFS CSI

| | RBD | CephFS |
|---|-----|--------|
| accessModes | RWO 为主 | RWO/RWX |
| 多 Pod 共享 | 需 RWX + 特殊配置 | 原生 RWX |

## 反模式

- K8s 使用 client.admin
- StorageClass 无 allowVolumeExpansion
- pool pg_num 过小

下一篇：**监控 Prometheus**。
