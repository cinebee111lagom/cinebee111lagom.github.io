---
title: MySQL SRE 告警规则与值班手册
date: 2026-08-14 11:00:00
tags:
  - MySQL
  - 告警
categories:
  - MySQL SRE
---

## P0 告警

```yaml
- alert: MySQLDown
  expr: mysql_up == 0
  for: 1m

- alert: MySQLReplicationStopped
  expr: mysql_slave_status_slave_sql_running == 0
  for: 2m

- alert: MySQLReplicationLagHigh
  expr: mysql_slave_status_seconds_behind_master > 300
  for: 5m

- alert: MySQLConnectionsHigh
  expr: mysql_global_status_threads_connected / mysql_global_variables_max_connections > 0.85
  for: 5m
```

## P1 告警

- 磁盘使用率 > 80%
- 慢查询 rate 突增 3 倍
- InnoDB 锁等待 > 10 持续 5m
- MGR 节点非 ONLINE

## 值班 Runbook

| 告警 | 第一步 | 第二步 |
|------|--------|--------|
| MySQLDown | systemctl status | 查 OOM/磁盘/错误日志 |
| 复制中断 | SHOW SLAVE STATUS | 跳过错误或 rebuild 从库 |
| 延迟高 | 查大事务 | 并行复制、拆事务 |
| 连接满 | 查 processlist | 杀 sleep 连接、扩 max_connections |

## 通知

```
P0 → 电话 + IM + 工单（5 分钟响应）
P1 → IM + 工单（30 分钟）
```

## 反模式

- 告警无 runbook
- 复制延迟阈值过小导致告警疲劳
- 未区分 staging/prod 告警路由

每季度 failover 演练验证告警有效性。
