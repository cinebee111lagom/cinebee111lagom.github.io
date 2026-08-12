---
title: Ceph 集群健康检查与状态解读
date: 2026-08-30 11:30:00
tags:
  - Ceph
  - 健康检查
  - 入门
categories:
  - Ceph 新手入门
---

`ceph -s` 是值班第一站，读懂颜色和字段才能快速判断严重程度。

## 健康状态

| 状态 | 含义 | 动作 |
|------|------|------|
| HEALTH_OK | 正常 | 无 |
| HEALTH_WARN | 警告 | 计划内处理 |
| HEALTH_ERR | 错误 | 尽快修复 |

## ceph -s 示例解读

```
  cluster:
    id:     xxxx
    health: HEALTH_WARN
    ...

  services:
    mon: 3 daemons, quorum node1,node2,node3
    mgr: node1(active), standbys: node2
    osd: 12 osds: 12 up, 12 in
    ...

  data:
    pools:   3 pools, 256 pgs
    objects: 1.2M, 4.5 TiB
    usage:   13 TiB used, 20 TiB avail
    pgs:     256 active+clean
```

| 字段 | 关注 |
|------|------|
| quorum | MON 是否多数在线 |
| osd up/in | up=进程活，in=在 CRUSH 内 |
| pgs active+clean | 理想状态 |
| degraded/recovering | 有副本不足或恢复中 |

## 常见 WARN

| 消息 | 含义 |
|------|------|
| OSD near full | OSD 使用率 > 85% |
| too many PGs per OSD | pg_num 过大 |
| MON clock skew | 时间不同步 |
| slow requests | 磁盘或网络慢 |

```bash
ceph health detail
```

## PG 状态速查

| 状态 | 说明 |
|------|------|
| active+clean | 正常 |
| active+degraded | 副本不足 |
| peering | 选举 Primary |
| backfilling | 数据迁移 |
| stuck inactive | 异常，需排查 |

## 日常巡检脚本

```bash
#!/bin/bash
ceph -s | head -20
ceph health detail | grep -v HEALTH_OK || true
ceph osd df tree | awk 'NR==1 || /%/ {print}'
```

## 反模式

- 忽略 WARN 直到变 ERR
- 不区分 recovering（正常）与 stuck
- 只看容量不看 PG 状态

下一篇：**OSD 管理与扩容**。
