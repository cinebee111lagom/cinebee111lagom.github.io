---
title: Ceph RBD 快照与克隆入门
date: 2026-08-30 12:45:00
tags:
  - Ceph
  - 快照
  - 入门
categories:
  - Ceph 新手入门
---

RBD **快照** 是时间点副本，**克隆** 可快速创建可写分支（CoW）。

## 创建快照

```bash
rbd snap create rbd_pool/vol1@snap1
rbd snap ls rbd_pool/vol1
```

## 回滚

```bash
# 需先 unmap 或确保无 IO
rbd snap rollback rbd_pool/vol1@snap1
```

## 保护快照（克隆前必须）

```bash
rbd snap protect rbd_pool/vol1@snap1
```

## 克隆

```bash
rbd clone rbd_pool/vol1@snap1 rbd_pool/vol1-clone1
rbd info rbd_pool/vol1-clone1
# 独立可写卷，仅存储与父快照差异
```

## 删除顺序

```
1. 删除所有 clone 或 flatten
2. rbd snap unprotect
3. rbd snap rm
```

```bash
rbd flatten rbd_pool/vol1-clone1   # 脱离父快照，占满空间
```

## K8s 中的快照

VolumeSnapshot CR + CSI 对接 RBD snap，用于 **备份/恢复 PVC**。

## 适用场景

| 场景 | 用法 |
|------|------|
| 升级前备份 | snap + rollback |
| 快速发环境 | clone |
| 数据库 | 配合 quiesce（应用一致） |

## 反模式

- 快照堆积不清理（元数据与空间压力）
- 未 protect 就 clone
- 生产 rollback 无应用层 quiesce

下一篇：**纠删码与副本**。
