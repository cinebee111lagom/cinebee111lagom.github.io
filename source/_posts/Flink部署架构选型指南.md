---
title: Flink 部署架构选型指南
date: 2026-08-18 09:15:00
tags:
  - Flink
  - 架构
categories:
  - Flink SRE
---

Flink 部署架构需结合作业数量、状态规模与团队运维能力选型。

## 部署模式

| 模式 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| Standalone | 开发/测试 | 简单 | 无资源隔离 |
| YARN Session | 多作业共享 | 资源复用 | 作业互相影响 |
| YARN/K8s Application | 生产推荐 | 一作业一集群、隔离好 | 启动稍慢 |
| Flink Operator (K8s) | 云原生 | GitOps、Savepoint 升级 | 学习成本 |

## 资源模型

```
JobManager (1~2 HA) → 调度、Checkpoint 协调
TaskManager × N     → Slot 运行 subtask
Slot                → 一个并行 subtask 的资源单元
```

## 选型决策树

```
作业数 < 5 且状态 < 10GB？
  ├─ 是 → K8s Application + Operator
  └─ 否 → 是否大状态 (>100GB)？
           ├─ 是 → 独立 TM 池 + RocksDB + 增量 Checkpoint
           └─ 否 → 共享 Session 集群（谨慎）
```

## State 与 Checkpoint 存储

| 存储 | 场景 |
|------|------|
| S3 / OSS | 生产 Checkpoint（推荐） |
| HDFS | 传统企业大数据栈 |
| 本地磁盘 | 仅开发 |

## 版本选择

- 生产推荐 **Flink 1.18/1.19** LTS 社区版
- Connector 版本与 Flink 严格匹配
- JDK 11（1.19+ 支持 JDK 17）

## 与 Kafka 集成架构

```
Kafka → Flink Application → Kafka / JDBC / ES
         ↓ Checkpoint (S3)
         ↓ Prometheus 监控
```

架构文档应包含：JM HA 方案、Checkpoint 路径、并行度基线、Savepoint 升级流程。
