---
title: Ceph CRUSH 规则与拓扑入门
date: 2026-08-30 12:00:00
tags:
  - Ceph
  - CRUSH
  - 入门
categories:
  - Ceph 新手入门
---

**CRUSH** 决定 PG 如何映射到 OSD，实现 **故障域隔离** 与 **权重均衡**。

## 拓扑层次

```
root (default)
 └── room (datacenter)
      └── rack
           └── host (ceph-node1)
                └── osd.0
                └── osd.1
```

## 查看 CRUSH

```bash
ceph osd crush tree
ceph osd crush rule ls
ceph osd crush rule dump replicated_rule
```

## 故障域

副本 pool `size=3` 时，CRUSH 尽量把 3 副本放在 **不同 host**（或 rack）：

```bash
ceph config set mon mon_osd_reporter_subtree_level host
```

## 权重（weight）

```bash
# 按容量比例设权重（TB）
ceph osd crush reweight osd.0 1.0
ceph osd crush reweight-all
```

权重决定 **数据分配比例**。

## 自定义 rule（概念）

```
# EC 或跨 rack 三副本时可定义 crush rule
# 新手先用 default replicated_rule
```

## 添加 host 到拓扑

cephadm 添加 host 时通常 **自动** 加入 CRUSH；手动：

```bash
ceph osd crush add-bucket ceph-node4 host
ceph osd crush move ceph-node4 root=default
ceph osd crush add osd.12 1.0 host=ceph-node4
```

## 反模式

- 所有 OSD 在同一 host 却要 3 副本（无法隔离）
- 手动改 CRUSH 无备份 map
- 不理解 weight 导致数据倾斜

下一篇：**K8s RBD CSI**。
