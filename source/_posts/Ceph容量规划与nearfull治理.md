---
title: Ceph 容量规划与 nearfull 治理
date: 2026-08-31 11:15:00
tags:
  - Ceph
  - SRE
  - 容量
categories:
  - Ceph SRE
---

**cluster full** 会导致 **全局只读**，容量是 Ceph SRE 最高优先级之一。

## 阈值体系

| 级别 | 默认 ratio | 行为 |
|------|------------|------|
| nearfull | 80% | WARN，计划扩容 |
| backfillfull | 85% | 限制 backfill |
| full | 90~95% | 禁止写 |

```bash
ceph osd df tree
ceph df detail
```

## 容量模型

```
raw 容量 × usable 比例（三副本约 33%）= 可用逻辑容量
usable = raw / replica_size × (1 - 预留 15%)
```

## 扩容手段

| 手段 | 速度 | 适用 |
|------|------|------|
| 加 OSD/盘 | 中 | 常规 |
| 加节点 | 中 | 大规模 |
| 删快照/RGW 生命周期 | 快 | 紧急 |
| 降副本（危险） | 快 | **不推荐** |

## 治理流程

```
周报：pool 用量 Top N
nearfull 告警 → 工单 → 7 天内扩容或清理
禁止在新 nearfull 集群上大删大建（trigger 大量 rebalance）
```

## RGW 生命周期

```json
{
  "Rules": [{
    "Expiration": { "Days": 90 },
    "ID": "expire-old",
    "Status": "Enabled"
  }]
}
```

## 反模式

- 90% 才扩容
- 无 per-pool quota
- 忽视 backfill 临时占满

**预留 15~20% 空闲** 为 recovery 与 backfill 缓冲。
