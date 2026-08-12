---
title: Ceph PG 均衡与 rebalance 生产治理
date: 2026-08-31 12:00:00
tags:
  - Ceph
  - SRE
  - PG
categories:
  - Ceph SRE
---

PG **不均或过多** 导致 OSD 热点、MON 压力、recovery 缓慢。

## 查看 PG 分布

```bash
ceph pg stat
ceph osd df tree
ceph pg dump pgs_brief | awk '{print $1}' | sort | uniq -c | sort -rn | head
```

## pg_num 规划

```
target pg_num = (OSDs × 100) / replica_size / num_pools
取最接近的 2^n
单 OSD PG 建议 50~200
```

## 扩容后增 PG

```bash
ceph osd pool set rbd_ssd pg_num 256
ceph osd pool set rbd_ssd pgp_num 256
# 触发 rebalance，业务低峰执行
```

## rebalance 控制

```bash
ceph osd set norebalance    # 维护窗口暂停
ceph osd unset norebalance

ceph config set osd osd_max_backfills 2
ceph config set global osd_recovery_sleep 0.1
```

## stuck PG 处理

```bash
ceph pg dump_stuck
ceph pg <pgid> query
# 常见：down OSD、权限、空间不足
ceph pg repair <pgid>   # 谨慎
```

## 变更窗口

| 操作 | 窗口 |
|------|------|
| pg_num 翻倍 | 低峰 |
| 新 pool 创建 | 任意 |
| crush rule 改 | 维护窗口 |

## 反模式

- pg_num=8192 小集群
- 高峰 pg split
- stuck PG 直接 force create

PG 变更 **先 staging 测 rebalance 时长**。
