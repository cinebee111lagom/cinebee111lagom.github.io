---
title: 阿里云 RDS 生产运维 SRE 实践
date: 2026-08-26 10:15:00
tags:
  - 阿里云
  - RDS
  - MySQL
categories:
  - 阿里云资源 SRE
---

RDS 托管数据库是生产核心，SRE 需关注高可用、备份、监控与参数。

## 版本与规格

| 项 | 生产建议 |
|----|----------|
| 系列 | 高可用版（主备双节点） |
| 架构 | 双 AZ 部署 |
| 版本 | MySQL 8.0 / PostgreSQL 16 |
| 规格 | 按 QPS/连接数压测定 |

## 网络与安全

```
VPC 私网访问
白名单：仅应用安全组 IP 段
禁止 0.0.0.0/0
SSL 连接（可选强制）
```

## 备份策略

| 类型 | 配置 |
|------|------|
| 自动备份 | 每日，保留 7~30 天 |
| 日志备份 | Binlog/WAL，支持 PITR |
| 跨地域备份 | 核心库开启 |

```bash
# 恢复演练：从备份创建实例到 staging
```

## 监控告警（CloudMonitor）

| 指标 | 告警 |
|------|------|
| CPUUtilization | > 80% P1 |
| DiskUsage | > 85% P1 |
| IOPSUsage | > 80% P2 |
| ConnectionUsage | > 80% P1 |
| ReplicationLag（只读） | > 30s P1 |

## 参数基线

```
max_connections：与连接池联动
innodb_buffer_pool_size：内存 70~80%
slow_query_log：ON
```

## 只读实例

```
写 → 主实例
读 → 只读实例（1~5 个）
注意只读延迟监控
```

## 变更流程

1. 参数修改 → 维护窗口
2. 小版本升级 → 先 staging
3. 规格升降 → 可在线（部分）

RDS SRE 与 **MySQL SRE / PostgreSQL SRE** 系列互补，云侧侧重控制台与托管能力。
