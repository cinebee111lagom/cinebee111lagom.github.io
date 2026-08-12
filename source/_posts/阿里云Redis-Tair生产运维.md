---
title: 阿里云 Redis/Tair 生产运维
date: 2026-08-26 10:30:00
tags:
  - 阿里云
  - Redis
  - Tair
categories:
  - 阿里云资源 SRE
---

阿里云 Redis 企业版 / Tair 是托管缓存，SRE 需关注内存、持久化与高可用。

## 架构选型

| 版本 | 适用 |
|------|------|
| 标准版 | 开发 |
| 高可用版 | 生产（主备） |
| 集群版 | 大内存、高 QPS |
| Tair 持久内存/磁盘型 | 成本优化 |

## 网络

```
VPC 私网
白名单：应用子网 CIDR
禁止公网访问
```

## 参数基线

```
maxmemory-policy：allkeys-lru 或 volatile-lru
timeout：300
# 持久化：根据 RPO 选 RDB/AOF（企业版）
```

## 监控告警

| 指标 | 告警 |
|------|------|
| MemoryUsage | > 80% P1 |
| ConnectionUsage | > 80% P1 |
| IntranetIn/Out 带宽 | 接近规格 P2 |
| FailedCount | > 0 P1 |

## 内存规划

```
峰值内存 × 1.3 余量
大 Key 治理（应用层 + 扫描工具）
```

## 备份

- 自动备份：每日，保留 7 天
- 手动备份：重大变更前

## 故障场景

| 场景 | 处理 |
|------|------|
| 主备切换 | 自动，查切换原因 |
| 内存满 | 扩容规格或清理 Key |
| 连接打满 | 应用连接池、排查泄漏 |

与 **Redis SRE** 系列对照，云侧增加白名单、监控模板与工单流程。
