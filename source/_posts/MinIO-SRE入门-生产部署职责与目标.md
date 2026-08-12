---
title: MinIO SRE 入门：生产部署职责与目标
date: 2026-09-02 09:00:00
tags:
  - MinIO
  - SRE
  - 对象存储
categories:
  - MinIO SRE
---

MinIO 是私有 **S3 基础设施**，SRE 目标是保障 **可用性、数据持久性、安全与成本** 在 SLA 内长期运行。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | 分布式拓扑、LB、TLS、Operator |
| 容量 | 磁盘/EC 利用率、lifecycle |
| 安全 | IAM、Policy、加密、审计 |
| 可观测 | Prometheus、告警、日志 |
| 灾备 | 桶复制、站点复制、mirror |
| 变更 | 版本升级、节点扩缩 |
| 集成 | K8s、Velero、GitLab、数据应用 |
| 性能 | 网络、磁盘、并发调优 |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| S3 API 可用性 | 99.9% ~ 99.95% |
| 数据持久性 | 11 9s（EC + 跨站点） |
| 单节点故障 | 业务无中断 |
| 容量告警提前量 | ≥ 7 天 |
| RPO（复制） | ≤ 15 分钟 |
| RTO（集群重建） | ≤ 4 小时 |

## 架构演进

```
单机 POC → 4+ 节点分布式 → LB + TLS
         → 桶/站点复制 DR
         → K8s Operator 多 Tenant
         → 混合云 tier（MinIO + 云 OSS）
```

## 与开发、平台的边界

- **应用**：Bucket 申请、SDK、presigned URL |
- **K8s/备份**：Velero、CSI 配置 |
- **MinIO SRE**：集群、IAM、监控、升级、Runbook |

本系列 20 篇覆盖 MinIO 从生产部署、监控、灾备到故障演练的完整 SRE 路径。
