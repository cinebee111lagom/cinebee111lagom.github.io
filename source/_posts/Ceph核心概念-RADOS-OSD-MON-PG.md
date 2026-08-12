---
title: Ceph 核心概念：RADOS、OSD、MON、PG
date: 2026-08-30 09:15:00
tags:
  - Ceph
  - 入门
categories:
  - Ceph 新手入门
---

理解这几个概念，是读懂 `ceph -s` 和后续运维的基础。

## RADOS

**Reliable Autonomic Distributed Object Store** — Ceph 的核心，所有数据以 **Object** 形式存在 RADOS 中，上层 RBD/CephFS/RGW 都是 RADOS 的客户端。

## MON（Monitor）

| 职责 | 说明 |
|------|------|
| 集群地图 | 维护 Cluster Map |
| 仲裁 | 通常 3 或 5 个（奇数） |
| 不存用户数据 | 仅存元数据 |

MON 宕 1 个（3 节点）集群仍可用，**不可只部署 1 个 MON**。

## OSD（Object Storage Daemon）

| 职责 | 说明 |
|------|------|
| 存数据 | 每块磁盘通常 1 OSD |
| 复制/纠删码 | 负责副本写入 |
| 恢复 | 故障盘自动 backfill |

OSD 是 **容量与性能的基本单元**。

## PG（Placement Group）

```
Pool → 多个 PG → PG 映射到 OSD 集合
```

| 作用 | 说明 |
|------|------|
| 逻辑分片 | 对象哈希到 PG |
| 控制迁移粒度 | PG 太多/太少都不好 |
| 均衡 | CRUSH 决定 PG 在哪些 OSD |

**对象 → PG → OSD**，是 Ceph 寻址链路。

## MGR（Manager）

- 提供 Dashboard、Prometheus 指标
- 通常 2 个（1 active + 1 standby）

## 关系图

```
Client
  ↓
MON（拿 Map）→ 知道对象在哪
  ↓
OSD（读写 Object）
  ↑
PG 决定对象落在哪组 OSD
```

## 反模式

- 只有 1 个 MON
- 不理解 PG 就暴力调 pool 参数
- 把 OSD 与 MON 混谈（职责不同）

下一篇：**架构与数据流**。
