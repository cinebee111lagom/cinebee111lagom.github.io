---
title: Ceph 性能调优与基准测试 SRE 实践
date: 2026-08-31 11:30:00
tags:
  - Ceph
  - SRE
  - 性能
categories:
  - Ceph SRE
---

性能问题需 **baseline + 分层定位**：网络 → 盘 → PG → 参数。

## 基准工具

```bash
# RADOS 层
ceph osd bench start -t 30
rados bench -p rbd_ssd 30 write --no-cleanup
rados bench -p rbd_ssd 30 seq

# RBD 层
rbd bench-write rbd_ssd/test --io-size 4K --io-threads 16 --io-total 1G
fio --name=rbd --ioengine=rbd --direct=1 --bs=4k --iodepth=32 \
    --rw=randwrite --pool=rbd_ssd --runtime=60
```

## 调优 checklist

| 层 | 项 |
|----|-----|
| 硬件 | NVMe、双 25G、JBOD HBA |
| 网络 | cluster 网独立、jumbo frame（需全网一致） |
| CRUSH | failure domain=host/rack |
| PG | pg_num 合理，无 imbalance |
| OSD | mClock profile、BlueStore cache |
| 客户端 | 多队列、cache=writethrough |

## 常见瓶颈

| 现象 | 原因 |
|------|------|
| 写延迟高 | HDD journal 慢 / 网络 |
| recovery 占满 IO | 调低 recovery 优先级 |
| 单 OSD 热点 | PG 不均，reweight |
| 小 IO 差 | 盘型或 pg 过多 |

## PG 均衡

```bash
ceph pg dump | grep unknown   # 检查
ceph osd reweight-by-utilization 120  # 谨慎使用
upmap-balancer  # 高级均衡
```

## 性能回归

版本升级、换盘、改 CRUSH 后 **重跑 fio baseline** 对比。

## 反模式

- 无 baseline 口头说「变慢了」
- 全 HDD 期望百万 IOPS
- 业务高峰调 rebalance

性能报告：**IOPS/带宽/P99 延迟 + 集群拓扑**。
