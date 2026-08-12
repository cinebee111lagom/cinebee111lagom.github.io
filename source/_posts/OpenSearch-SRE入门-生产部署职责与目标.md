---

## title: OpenSearch SRE 入门：生产部署职责与目标
date: 2026-08-20 09:00:00
tags:
  - OpenSearch
  - SRE
categories:
  - OpenSearch SRE

OpenSearch 是搜索与日志分析核心基础设施，SRE 目标是让集群在**可用性、查询延迟、存储成本**下长期稳定运行。

## SRE 职责


| 领域   | 内容                         |
| ---- | -------------------------- |
| 部署   | 架构选型、节点规划、K8s/裸机           |
| 高可用  | 副本、cluster_manager 选举、跨 AZ |
| 备份   | Snapshot 仓库、定时快照、恢复演练      |
| 容量   | 分片数、磁盘、JVM、写入吞吐            |
| 可观测  | 集群健康、慢查询、GC、磁盘             |
| 变更   | 滚动升级、索引模板、mapping 变更       |
| 安全   | Security 插件、RBAC、TLS       |
| 生命周期 | ISM 热温冷删、日志滚动              |


## 生产 SLA 参考


| 指标        | 目标                 |
| --------- | ------------------ |
| 集群可用性     | 99.9% ~ 99.95%     |
| 搜索 P99 延迟 | < 500ms（日志场景）      |
| 写入延迟      | bulk 成功率 > 99.9%   |
| RPO       | ≤ 24h（快照）或近实时（CCR） |
| RTO       | ≤ 1h（从快照恢复）        |


## 架构演进路径

```
单节点 → 3 节点集群 → 专用角色分离
      → 热温冷 ISM → Cross-Cluster Replication
      → K8s Operator /  AWS OpenSearch Service
```

## 与开发、平台的边界

- **开发**：mapping 设计、查询 DSL、索引命名
- **SRE**：集群部署、快照、扩容、升级、Security
- **日志平台**：Filebeat/Logstash 采集规则

本系列 20 篇覆盖 OpenSearch 从部署、HA、备份、监控到容灾演练的完整 SRE 路径。