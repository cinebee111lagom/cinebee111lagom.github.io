---
title: MySQL 多机房容灾与读写切换
date: 2026-08-14 13:15:00
tags:
  - MySQL
  - 容灾
categories:
  - MySQL SRE
---

## 架构模式

### 同城双机房

```
机房 A（主） ──半同步/异步──► 机房 B（从）
Orchestrator / MGR 跨机房 failover
```

RPO：0~数秒（半同步）；RTO：分钟级。

### 异地灾备

```
生产 ──异步复制──► 异地只读 / 冷备
或 binlog + 对象存储 → DR 恢复
```

RPO：分钟~小时；适合非实时 DR。

## 半同步复制

```sql
INSTALL PLUGIN rpl_semi_sync_source SONAME 'semisync_source.so';
SET GLOBAL rpl_semi_sync_source_enabled = 1;
SET GLOBAL rpl_semi_sync_source_timeout = 1000;
```

至少 1 从库 ACK 才提交，降低丢数据风险。

## 切换流程

1. 确认主库不可达 / 计划切换
2. Orchestrator 提升从库 / MGR 自动选主
3. 更新 DNS / ProxySQL 后端
4. 应用重连（连接池刷新）
5. 验证读写与复制

## 演练

- 季度断主演练
- 记录 RTO、数据一致性校验结果

## 云方案

- RDS 跨 AZ / 跨 Region Read Replica
- SRE 重点：复制 lag 告警与切换 runbook

多机房**不是多写**，除非 Sharding 或 CRDT 等特殊设计。
