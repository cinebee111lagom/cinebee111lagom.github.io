---
title: Ceph 与 OpenStack 集成入门
date: 2026-08-30 13:30:00
tags:
  - Ceph
  - OpenStack
  - 入门
categories:
  - Ceph 新手入门
---

**OpenStack + Ceph** 是私有云经典组合：Cinder（块）、Glance（镜像）、Nova（VM）共用 RADOS。

## 集成组件

| OpenStack | Ceph 用法 |
|-----------|-----------|
| Cinder | RBD 卷 → VM 盘 |
| Glance | RBD 或 Swift 存镜像 |
| Nova | libvirt 直连 RBD |
| Manila | CephFS 共享（可选） |

## Cinder 配置要点（概念）

```ini
# cinder.conf
[DEFAULT]
enabled_backends = ceph

[ceph]
volume_driver = cinder.volume.drivers.rbd.RBDDriver
rbd_pool = volumes
rbd_user = cinder
rbd_ceph_conf = /etc/ceph/ceph.conf
```

Ceph 侧创建 `client.cinder` 与 `volumes` pool。

## Glance 后端

```ini
# glance.conf
stores = rbd
default_store = rbd
rbd_store_pool = images
```

## 优势

- VM 盘与镜像都在 Ceph，**无单点 NAS**
- 快照/克隆与 OpenStack 卷操作联动
- 与 K8s 可 **共用集群不同 pool**

## 与 K8s 共存

```
同一 Ceph 集群：
  pool: volumes     → OpenStack Cinder
  pool: kubernetes  → K8s CSI
  pool: rgw         → 对象
```

## 反模式

- Cinder/Glance 共用 client.admin
- 单 pool 无配额混所有租户
- OpenStack 网络与 Ceph 复制网冲突

无 OpenStack 时可跳过，重点看 **RBD CSI** 篇。
