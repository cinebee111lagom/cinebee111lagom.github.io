---
title: Ceph 存储池 Pool 创建与管理入门
date: 2026-08-30 10:15:00
tags:
  - Ceph
  - Pool
  - 入门
categories:
  - Ceph 新手入门
---

**Pool** 是 Ceph 逻辑隔离单元，类似「命名空间 + 策略」。

## 查看 Pool

```bash
ceph osd lspools
ceph osd pool ls detail
```

## 创建副本 Pool

```bash
ceph osd pool create rbd_pool 128 128
ceph osd pool set rbd_pool size 3
ceph osd pool application enable rbd_pool rbd
```

| 参数 | 含义 |
|------|------|
| 128（第一个） | PG 数量（2 的幂，按 OSD 数估算） |
| 128（第二个） | PGP（通常与 pg_num 相同） |
| size 3 | 3 副本 |

## PG 数量粗算

```
pg_num ≈ (OSD 总数 × 100) / 副本数 / pool 数
取最接近的 2 的幂
```

过小：数据不均；过大：MON 压力大。

## 常用管理

```bash
# 重命名
ceph osd pool rename old new

# 设置配额
ceph osd pool set-quota rbd_pool max_bytes 1T

# 删除（危险，需无数据）
ceph osd pool rm pool_name pool_name --yes-i-really-really-mean-it
```

## Pool 类型

| 类型 | 创建 |
|------|------|
| replicated | `pool create` + `size N` |
| erasure | `ceph osd pool create ec_pool 64 erasure myprofile` |

新手默认 **replicated size=3**。

## 应用标签

启用 RBD/CephFS/RGW 前必须：

```bash
ceph osd pool application enable <pool> rbd
ceph osd pool application enable <pool> cephfs
ceph osd pool application enable <pool> rgw
```

## 反模式

- pg_num=32 跑 50 个 OSD
- 生产 pool 无 size 显式设置
- 一个 pool 混所有业务

下一篇：**RBD 块存储**。
