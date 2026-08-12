---
title: 阿里云 RDS 生产运维
date: 2026-08-25 10:30:00
tags:
  - 阿里云
  - RDS
categories:
  - 阿里云资源 SRE
---

RDS 托管数据库是生产首选，SRE 需掌握高可用、备份、监控与参数基线。

## 系列选型

| 系列 | 说明 |
|------|------|
| 高可用系列 | 一主一备，跨 AZ（生产必选） |
| 集群系列 | PolarDB，读写分离扩展 |
| 基础版 | 单节点，仅 dev |

## 规格与存储

```
MySQL 8.0 高可用
规格：mysql.n2.medium.1 起步，按 QPS 压测扩容
存储：ESSD 自动扩容开启
```

## 网络与安全

- **VPC 私网**，仅应用安全组可访问
- 白名单：安全组方式（非 0.0.0.0/0）
- SSL 连接（应用侧 verify）
- 高权限账号隔离，应用只读/读写分离账号

## 备份策略

| 类型 | 配置 |
|------|------|
| 自动备份 | 每日 02:00，保留 7~30 天 |
| 日志备份 | binlog，PITR |
| 跨 Region 备份 | 异地容灾（可选） |

```bash
# 控制台或 API 创建手动备份（变更前）
aliyun rds CreateBackup --DBInstanceId rm-xxx
```

## 监控告警

| 指标 | 告警 |
|------|------|
| CPUUtilization | > 80% |
| DiskUsage | > 85% |
| IOPSUsage | > 80% |
| ConnectionUsage | > 80% |
| ReplicationLag | > 30s（只读） |

## 参数模板

- 使用「高可用优化」参数模板
- 自定义：`max_connections`、慢 SQL、`innodb_buffer_pool`

## 变更流程

1. 变更前手动备份
2. 低峰窗口
3. 可运维时间段内操作
4. 主备切换演练（季度）

## 与自建 MySQL SRE 对照

本博客 **MySQL SRE** 系列的 Patroni、备份逻辑由 RDS 托管，SRE 聚焦**规格、备份、监控、账号**。

## Checklist

- [ ] 高可用 + 跨 AZ
- [ ] 自动备份 + 恢复演练
- [ ] 监控 P0/P1 告警
- [ ] 只读实例（读扩展）

RDS **禁止公网暴露**（生产）。
