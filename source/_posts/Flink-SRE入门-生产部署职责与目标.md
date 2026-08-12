---
title: Flink SRE 入门：生产部署职责与目标
date: 2026-08-18 09:00:00
tags:
  - Flink
  - SRE
categories:
  - Flink SRE
---

Flink 是实时计算核心引擎，SRE 目标是让流作业在**可用性、延迟、状态一致性**下 7×24 稳定运行。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | Session/Application 模式、K8s Operator |
| 高可用 | JM HA、Checkpoint、Savepoint |
| 状态 | RocksDB 调优、State TTL、大状态治理 |
| 容量 | 并行度、Slot、TM 内存、Checkpoint 存储 |
| 可观测 | 反压、Checkpoint、延迟、Kafka Lag |
| 变更 | Savepoint 升级、扩缩容、作业迁移 |
| 安全 | Kerberos、SSL、Secret 管理 |
| 容灾 | 跨 Region Savepoint、双集群 |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| 作业可用性 | 99.9% ~ 99.95% |
| 端到端延迟 P99 | < 5s（视业务） |
| Checkpoint 成功率 | > 99% |
| Checkpoint 耗时 | < 3 分钟（常规状态） |
| 故障恢复 RTO | ≤ 10 分钟（从 Checkpoint） |

## 架构演进路径

```
Standalone 开发 → YARN Session → K8s Application 模式
              → Flink Operator + S3 Checkpoint
              → 多集群 + 双活/主备
              → 云托管（Ververica / Confluent Cloud）
```

## 与开发、数据平台的边界

- **开发**：作业逻辑、状态设计、Watermark、Sink 幂等
- **SRE**：集群资源、Checkpoint 存储、监控告警、升级回滚
- **Kafka/DB SRE**：Source/Sink 侧容量与 ACL

本系列 20 篇覆盖 Flink 从部署、HA、Checkpoint、监控到容灾演练的完整 SRE 路径。
