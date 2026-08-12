---
title: Ceph SRE 入门：生产部署职责与目标
date: 2026-08-31 09:00:00
tags:
  - Ceph
  - SRE
  - 存储
categories:
  - Ceph SRE
---

Ceph 是私有云与 K8s 的 **统一存储底座**，SRE 目标是保障 **可用性、数据安全、容量与性能** 长期可运维。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | cephadm HA、网络分区、硬件选型 |
| 容量 | OSD 扩容、nearfull 治理、pool 配额 |
| 性能 | 盘型分层、PG 调优、网络带宽 |
| 可观测 | Prometheus、告警、Dashboard |
| 变更 | 版本升级、OSD 换盘、CRUSH 变更 |
| 备份 | RBD snap、RGW sync、配置备份 |
| 安全 | cephx、网络 ACL、RGW TLS |
| 集成 | K8s CSI、OpenStack Cinder |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| 集群可用性 | 99.9% ~ 99.95% |
| RBD IO 可用 | 单 OSD 故障无中断（3 副本） |
| 数据持久性 | 0 不可恢复丢失（多副本+备份） |
| nearfull 发现 | ≤ 15 分钟 |
| OSD 故障恢复 | PG clean ≤ 24h（视数据量） |
| 升级 RTO | 计划内 ≤ 4h |

## 架构演进

```
3 节点 all-in-one → 分离 MON/OSD → NVMe+ HDD 分层
                → 多 Rack CRUSH → RGW 多站点
                → Rook on K8s / 专用存储集群
```

## 与开发、平台的边界

- **业务/开发**：PVC 规格、S3 bucket 申请 |
- **K8s/OpenStack**：StorageClass、Cinder 配置 |
- **Ceph SRE**：集群、pool、OSD、监控、Runbook |

本系列 20 篇覆盖 Ceph 从生产部署、监控、灾备到故障演练的完整 SRE 路径。
