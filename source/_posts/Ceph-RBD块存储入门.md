---
title: Ceph RBD 块存储入门
date: 2026-08-30 10:30:00
tags:
  - Ceph
  - RBD
  - 入门
categories:
  - Ceph 新手入门
---

**RBD（RADOS Block Device）** 提供块设备，是虚拟机与 K8s 最常用接口。

## 创建镜像

```bash
# pool 需 enable rbd
rbd create rbd_pool/vol1 --size 10G
rbd ls rbd_pool
rbd info rbd_pool/vol1
```

## 本地映射（Linux Client）

```bash
# 安装客户端
apt install ceph-common   # 或 yum install ceph-common

# 复制集群配置
scp root@ceph-node1:/etc/ceph/ceph.conf /etc/ceph/
scp root@ceph-node1:/etc/ceph/ceph.client.admin.keyring /etc/ceph/

# 映射
rbd map rbd_pool/vol1
lsblk   # 出现 /dev/rbd0

# 格式化挂载
mkfs.xfs /dev/rbd0
mkdir -p /mnt/rbd && mount /dev/rbd0 /mnt/rbd

# 卸载
umount /mnt/rbd
rbd unmap rbd_pool/vol1
```

## 调整大小

```bash
rbd resize rbd_pool/vol1 --size 20G
# 客户端内 growpart/xfs_growfs 扩展文件系统
```

## 导出/导入

```bash
rbd export rbd_pool/vol1 vol1.img
rbd import vol1.img rbd_pool/vol2
```

## 典型场景

| 场景 | 说明 |
|------|------|
| KVM/QEMU | `-drive rbd=...` |
| OpenStack | Cinder backend |
| Kubernetes | RBD CSI PV |

## 反模式

- 不 enable rbd application
- 多客户端无集群文件系统却 RW 同挂载（需 GFS/OCFS2 或单写者）
- 映射后不设开机自动 unmap

下一篇：**CephFS 文件存储**。
