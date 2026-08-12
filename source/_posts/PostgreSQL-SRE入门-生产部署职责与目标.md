---
title: PostgreSQL SRE 入门：生产部署职责与目标
date: 2026-08-15 09:00:00
tags:
  - PostgreSQL
  - SRE
categories:
  - PostgreSQL SRE
---

PostgreSQL 是开源 OLTP/OLAP 的核心选择，SRE 目标是让它在**可用性、一致性、性能**之间长期稳定运行。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | 架构选型、安装、参数基线 |
| 高可用 | 流复制、Patroni、Proxy failover |
| 备份恢复 | pg_dump、pg_basebackup、WAL 归档、PITR |
| 容量 | 连接数、磁盘、QPS、shared_buffers、WAL 空间 |
| 可观测 | pg_stat_*、pg_stat_statements、日志 |
| 变更 | 升级、DDL、扩缩容、VACUUM |
| 安全 | 角色权限、SSL、审计、网络隔离 |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| 可用性 | 99.95% ~ 99.99% |
| RPO | ≤ 5 分钟（同步/异步复制 + WAL 归档） |
| RTO | ≤ 15 分钟（Patroni 自动/半自动切换） |
| P99 查询 | < 50ms（简单 OLTP） |

## 架构演进路径

```
单机 → 流复制读写分离 → Patroni HA + HAProxy → Citus/分片 + 中间件
```

## 与 DBA、开发的边界

- **开发**：表设计、索引建议、SQL 写法、迁移脚本
- **SRE/DBA**：部署、备份、切换、监控、容量、VACUUM 策略
- **安全**：合规、脱敏、访问审计

本系列 20 篇覆盖 PostgreSQL 从部署、HA、备份、监控到故障演练的完整 SRE 路径。
