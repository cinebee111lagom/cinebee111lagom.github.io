---
title: Ceph OSD 生产运维与换盘 Runbook
date: 2026-08-31 11:00:00
tags:
  - Ceph
  - SRE
  - OSD
categories:
  - Ceph SRE
---

OSD 是容量与故障 **第一线**，换盘/out 必须标准化。

## 计划内下线 OSD

```bash
# 1. 标记 out
ceph osd out osd.15

# 2. 等待 PG active+clean
watch -n10 ceph -s

# 3. 停止 daemon
ceph orch daemon stop osd.15

# 4. 维护物理盘...

# 5. 若永久移除
ceph orch daemon rm osd.15 --force
ceph osd crush remove osd.15
ceph auth del osd.15
ceph osd rm 15
```

## 换盘（同 slot 新盘）

```bash
ceph osd out osd.15
# wait clean
ceph orch daemon rm osd.15 --force
# 更换物理磁盘
wipefs -a /dev/sdX
ceph orch daemon add osd ceph-node3:/dev/sdX
# 新 OSD id，数据 backfill
```

## 意外磁盘故障

```
1. OSD 自动 down → HEALTH_WARN degraded
2. 确认硬件故障（smartctl -a）
3. out 故障 OSD（若未自动）
4. 换盘 + add osd
5. 观察 backfill 带宽
```

## 限流 recovery（业务高峰）

```bash
ceph config set osd osd_max_backfills 1
ceph config set osd osd_recovery_max_active 1
# 低峰恢复默认
```

## 禁止操作

- 未 out 直接拔盘
- 同时 out >1 个 OSD（除非容量充足且明确计划）
- full 状态下 out OSD

## CMDB 记录

OSD id、WWN、slot、上架日期、故障次数。
