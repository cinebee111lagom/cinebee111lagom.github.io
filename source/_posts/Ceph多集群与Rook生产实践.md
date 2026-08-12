---
title: Ceph 多集群与 Rook 生产实践
date: 2026-08-31 13:00:00
tags:
  - Ceph
  - SRE
  - Rook
categories:
  - Ceph SRE
---

**专用 Ceph 集群** vs **Rook 跑在 K8s** 是两种主流生产形态。

## 选型

| | 专用 cephadm | Rook |
|---|--------------|------|
| 运维 | 存储团队 | K8s + 存储 |
| 性能 | 通常更优 | 依赖 K8s 网络/盘 |
| 生命周期 | 独立升级 | 随 K8s 编排 |
| 适用 | 大规模/OpenStack | 云原生 K8s 为主 |

## Rook 架构

```
Rook Operator
  → CephCluster CR
  → MON/OSD/MGR Pod on K8s nodes
  → CSI provisioner
```

## Rook 生产要点

| 项 | 建议 |
|----|------|
| 节点 label | 存储专用节点 |
| OSD | 裸盘 / LV，勿用 loop |
| 资源 | MON/OSD request/limit |
| 升级 | operator → cluster 分步 |

```yaml
# CephCluster 片段
spec:
  mon:
    count: 3
    allowMultiplePerNode: false
  storage:
    useAllNodes: false
    useAllDevices: false
    nodes:
      - name: "node1"
        devices:
          - name: "sdb"
```

## 多集群

```
ceph-adm-prod   → OpenStack + 大 K8s
rook-dev        → 开发 K8s 内置
```

**不要** 一个小 Rook 集群扛全公司生产。

## 反模式

- Worker 节点混 OSD 无隔离
- Rook 集群无独立备份
- 升级 operator 不读 release note

Rook 问题查 **operator log + ceph tools pod**。
