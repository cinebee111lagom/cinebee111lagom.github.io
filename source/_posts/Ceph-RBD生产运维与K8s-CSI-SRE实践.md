---
title: Ceph RBD 生产运维与 K8s CSI SRE 实践
date: 2026-08-31 12:15:00
tags:
  - Ceph
  - SRE
  - RBD
categories:
  - Ceph SRE
---

K8s 是 RBD **最大消费方**，SRE 需治理 **StorageClass、快照、扩容**。

## Pool 隔离

```
kubernetes_prod  → 生产 SC
kubernetes_dev   → 开发 SC
不同 cephx user + 不同 pool
```

## CSI 运维

```bash
# 查看 CSI pod
kubectl -n ceph-csi get pods

# 常见：mon 列表过期
kubectl -n ceph-csi logs deploy/rbd-provisioner
```

## Volume 扩容

StorageClass `allowVolumeExpansion: true`

```bash
kubectl patch pvc mypvc -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
# CSI ControllerExpand 在线扩卷 + 文件系统扩展
```

## 快照与备份

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: mysnap
spec:
  volumeSnapshotClassName: csi-rbd-snapclass
  source:
    persistentVolumeClaimName: mypvc
```

Velero + CSI snapshot 做 **namespace 级 DR**。

## 故障

| 问题 | 排查 |
|------|------|
| PVC Pending | SC、pool 满、csi 日志 |
| Mount timeout | mon 网络、keyring |
| Multi-attach error | RWO 被两 Pod 用 |

## 反模式

- 生产/dev 共 pool 无 quota
- 无 VolumeSnapshotClass
- admin key 在 CSI secret

RBD 用量 **按 namespace/tenant** 报表。
