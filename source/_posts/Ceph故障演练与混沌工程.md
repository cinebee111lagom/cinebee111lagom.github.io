---
title: Ceph 故障演练与混沌工程
date: 2026-08-31 12:45:00
tags:
  - Ceph
  - SRE
  - 混沌工程
categories:
  - Ceph SRE
---

存储故障影响面大，**staging 演练** 验证 HA 与 Runbook 可执行。

## 演练场景（staging）

| 场景 | 操作 | 验证 |
|------|------|------|
| 单 OSD down | stop osd.N | degraded→clean |
| 单 MON down | stop mon | quorum 2/3 |
| 单节点宕机 | shutdown node | PG recovery |
| 网络分区 | iptables drop cluster net | 业务影响评估 |
| 磁盘满 | 填测试 pool | nearfull 告警 |
| MGR failover | stop active mgr | 指标续 |

## 业务验证

```
1. fio 持续读写背景
2. 注入故障
3. 记录 IO 中断时间
4. K8s Pod PVC 是否 Hung
5. 告警触达时间
```

## 恢复演练

```
从 RBD snap export 恢复到新卷
从 backup crush+config 建新集群（年度）
```

## 成功标准

- P0 告警 ≤ 5min
- 无未文档化操作
- RTO 符合 SLA
- IO 中断在预期内（单 OSD 三副本应无感）

## 频率

| 演练 | 周期 |
|------|------|
| OSD/MON 故障 | 季 |
| 备份 restore | 半年 |
| 全节点灾难 | 年（ tabletop + 部分实操） |

## 反模式

- prod 直接 chaos
- 演练不记录 RTO
- 无业务方参与验证

演练报告进 **SRE 季度复盘**。
