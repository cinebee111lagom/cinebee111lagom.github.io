---
title: Ceph 生产部署架构选型指南
date: 2026-08-31 09:15:00
tags:
  - Ceph
  - SRE
  - 架构
categories:
  - Ceph SRE
---

Ceph 生产架构决定 **故障域、性能上限与运维复杂度**。

## 部署模式

| 模式 | 说明 | 适用 |
|------|------|------|
| 专用裸金属集群 | cephadm on BM | 大规模生产 |
| 超融合 | 计算+存储同节点 | 中小私有云 |
| Rook on K8s | Ceph 跑在 K8s | 云原生优先 |
| 分离式 | MON/MGR 轻量，OSD 重 | 大规模 |

## 最小生产

| 组件 | 数量 |
|------|------|
| MON | 3 或 5（奇数） |
| MGR | 2 |
| OSD 节点 | ≥ 3 |
| 副本 | size=3, min_size=2 |

## 硬件选型

| 层级 | 盘型 | 用途 |
|------|------|------|
| DB/WAL | NVMe | BlueStore DB/ WAL |
| 数据 | NVMe / SATA SSD | 热数据 |
| 冷 | HDD | RGW/归档 EC |

## 网络

```
Public network：Client / K8s CSI ↔ OSD
Cluster network：OSD ↔ OSD 复制/恢复
```

**25Gb+** 用于全闪高 IOPS；复制网与业务网 **必须分离**（生产）。

## Pool 规划

```
rbd_ssd      → VM/K8s 热卷
rbd_hdd      → 冷卷
cephfs_data  → 共享文件
rgw          → 对象（可 EC pool）
```

## 反模式

- 2 节点「伪 HA」
- HDD 与 NVMe 混 pool 无 tiering
- 单交换机无冗余

选型文档含：**容量 3 年预测、IOPS 需求、RPO/RTO**。
