---
title: Ceph CephFS 文件存储入门
date: 2026-08-30 10:45:00
tags:
  - Ceph
  - CephFS
  - 入门
categories:
  - Ceph 新手入门
---

**CephFS** 提供 POSIX 兼容共享文件系统，多客户端可同时挂载。

## 创建 CephFS

```bash
# 需要两个 pool：data + metadata（可复用或新建）
ceph osd pool create cephfs_data 64
ceph osd pool create cephfs_metadata 64

ceph fs new myfs cephfs_metadata cephfs_data

# 部署 MDS（Metadata Server）
ceph orch apply mds myfs --placement="3 ceph-node1 ceph-node2 ceph-node3"

ceph fs ls
ceph fs status myfs
```

## 客户端挂载

```bash
# 内核挂载（推荐 Linux）
mkdir /mnt/cephfs
mount -t ceph ceph-node1:6789:/ /mnt/cephfs -o name=admin,secret=<key>

# 或使用 ceph-fuse
ceph-fuse /mnt/cephfs
```

密钥从 `ceph auth get-key client.admin` 或创建专用 client。

## 创建限制权限的 Client

```bash
ceph auth get-or-create client.fsuser mon 'allow r' mds 'allow rw' osd 'allow rw pool=cephfs_data' -o /etc/ceph/ceph.client.fsuser.keyring
```

## 与 RBD 对比

| | RBD | CephFS |
|---|-----|--------|
| 接口 | 块设备 | 文件路径 |
| 共享 | 需集群 FS | 原生多客户端 |
| 适用 | VM 盘 | 共享目录、HPC |
| K8s | RBD CSI | CephFS CSI |

## 子目录隔离

```bash
ceph fs subvolume create myfs subvol1
# K8s CSI 常用 subvolume 做租户隔离
```

## 反模式

- 仅 1 个 MDS 无 standby（生产）
- metadata pool 与 data pool 混同一小 pool
- 大文件海量小文件不调 MDS cache

下一篇：**RGW 对象存储**。
