---
title: Ceph 备份与灾难恢复 SRE 实践
date: 2026-08-31 10:30:00
tags:
  - Ceph
  - SRE
  - 备份
categories:
  - Ceph SRE
---

Ceph 自带冗余 **≠ 备份**，误删、逻辑错误、多 OSD 故障仍需 DR。

## 备份层次

| 层级 | 方式 |
|------|------|
| RBD | 定时 snap + export 异地 |
| CephFS | snap/subvolume snap |
| RGW | bucket replication / rclone sync |
| 配置 | /etc/ceph、ceph config dump、CRUSH map |

## RBD 备份脚本

```bash
#!/bin/bash
POOL=rbd_ssd
VOL=prod-db-01
SNAP=backup-$(date +%Y%m%d)
rbd snap create ${POOL}/${VOL}@${SNAP}
rbd export ${POOL}/${VOL}@${SNAP} /backup/${VOL}-${SNAP}.img
rbd snap rm ${POOL}/${VOL}@${SNAP}  # 可选，保留 snap 则跳过
```

## 集群级

```bash
ceph osd getcrushmap -o crushmap.bin
ceph config dump > config-backup-$(date +%F).json
```

## RGW 多站点（EE/高级）

Primary → Secondary 异步复制，RPO 分钟级。

## 恢复演练

| 场景 | 频率 |
|------|------|
| RBD import 恢复单卷 | 季 |
| 新集群 restore crush+config | 半年 |
| 整 pool 误删 | 文档化（难恢复，靠备份） |

## RPO/RTO

| 业务 | RPO | RTO |
|------|-----|-----|
| 核心 DB 卷 | 1h snap | 2h |
| 对象冷存 | 24h | 8h |

## 反模式

- 仅 3 副本无 offsite
- snap 只在 Ceph 内不 export
- 从未 restore 演练

**误删 pool 几乎不可恢复**，权限与审批严控。
