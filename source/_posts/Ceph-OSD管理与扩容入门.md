---
title: Ceph OSD 管理与扩容入门
date: 2026-08-30 11:45:00
tags:
  - Ceph
  - OSD
  - 入门
categories:
  - Ceph 新手入门
---

**扩容加 OSD**、**换盘**、**下线节点** 是运维最常见操作。

## 扩容：加新盘

```bash
# 新节点加入集群
ceph orch host add ceph-node4 10.0.0.14

# 查看可用设备
ceph orch device ls ceph-node4

# 添加 OSD
ceph orch daemon add osd ceph-node4:/dev/sdb

# 或自动使用所有可用盘
ceph orch apply osd --all-available-devices --unmanaged=false
```

数据通过 **backfill** 自动 rebalance，期间集群可能 WARN。

## 查看 OSD 权重与使用

```bash
ceph osd tree
ceph osd df tree
ceph osd perf                  # 延迟
```

## 安全下线 OSD

```bash
# 1. 标记 out（数据迁出）
ceph osd out osd.5

# 2. 等待 PG active+clean
watch ceph -s

# 3. 停止 daemon
ceph orch daemon stop osd.5

# 4. 删除
ceph orch daemon rm osd.5 --force

# 5. 从 CRUSH 移除
ceph osd crush remove osd.5
ceph auth del osd.5
ceph osd rm 5
```

**切勿**直接拔盘不 out。

## 换盘（同 slot）

```
1. ceph osd out <id>
2. 等待 clean
3. stop + rm daemon
4. 换物理盘
5. ceph orch daemon add osd <host>:/dev/sdX
6. 新 OSD 获得新 id，数据 rebalance
```

## 反模式

- 单 OSD 满导致 cluster full（写阻塞）
- 同时 out 过多 OSD
- 扩容高峰期无监控

下一篇：**CRUSH 规则与拓扑**。
