---
title: Ceph 纠删码与副本策略入门
date: 2026-08-30 13:00:00
tags:
  - Ceph
  - 纠删码
  - 入门
categories:
  - Ceph 新手入门
---

**副本（Replication）** 简单可靠；**纠删码（Erasure Code）** 省空间但 CPU/延迟更高。

## 副本 Pool

```bash
ceph osd pool create rep_pool 128
ceph osd pool set rep_pool size 3
ceph osd pool set rep_pool min_size 2
```

| 参数 | 含义 |
|------|------|
| size 3 | 3 份副本 |
| min_size 2 | 至少 2 份可写（1 OSD 挂仍可写） |

**适用**：RBD、低延迟业务。

## 纠删码 Pool

```bash
ceph osd erasure-code-profile set ecprofile k=4 m=2 crush-failure-domain=host
ceph osd pool create ec_pool 64 64 erasure ecprofile
```

| 参数 | 含义 |
|------|------|
| k=4 | 4 数据块 |
| m=2 | 2 校验块 |
| 容忍 | 最多 2 OSD 故障 |
| 空间 | 约 1.5x（vs 3x 三副本） |

**适用**：RGW 冷数据、备份、大对象。

## 对比

| | 3 副本 | EC 4+2 |
|---|--------|--------|
| 空间效率 | 33% | ~67% |
| 写延迟 | 低 | 较高 |
| 恢复流量 | 1 份 | 多块 |
| 运维 | 简单 | 稍复杂 |

## RBD 用 EC

需 **EC overwrites** 支持（较新版本），或 RBD 用 replicated、RGW 用 EC **分离 pool**（常见）。

## 选择建议

```
VM 盘 / 数据库     → replicated size=3
对象归档 / 备份    → erasure code
混合               → 多 pool 分业务
```

## 反模式

- 所有业务强行 EC 省空间
- min_size=1（丢 2 副本仍写，数据风险）
- 小集群 k+m 过大导致 OSD 不足

下一篇：**常见问题与排查**。
