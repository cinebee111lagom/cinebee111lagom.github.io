---
title: MySQL 恢复与 PITR 点时间恢复
date: 2026-08-14 10:30:00
tags:
  - MySQL
  - 恢复
categories:
  - MySQL SRE
---

误删数据、机房故障都需要**可执行的恢复流程**，PITR 精确到秒。

## 全量恢复（xtrabackup）

```bash
systemctl stop mysqld
rm -rf /var/lib/mysql/*
xtrabackup --copy-back --target-dir=/backup/full-2026-08-14
chown -R mysql:mysql /var/lib/mysql
systemctl start mysqld
```

## PITR 流程

1. 恢复最近全量备份到目标时刻之前
2. 应用 binlog 到指定时间点：

```bash
mysqlbinlog --stop-datetime="2026-08-14 10:25:00" \
  mysql-bin.000123 mysql-bin.000124 | mysql -u root -p
```

或按 GTID：

```bash
mysqlbinlog --include-gtids='uuid:1-1000' binlog | mysql -p
```

## 误删表应急

```sql
-- 若有 flashback 工具或从 binlog 解析反向 SQL
-- 或从延迟从库（delayed replica）读取
```

延迟从库：`CHANGE MASTER TO MASTER_DELAY = 3600;`（1 小时缓冲）。

## RTO 优化

- 预置恢复脚本与检查清单
- 测试环境 quarterly 演练
- 文档化「从报警到恢复完成」各步骤耗时

## Runbook 摘要

| 场景 | 动作 |
|------|------|
| 整库损坏 | 最近全量 + binlog |
| 误 DELETE | binlog flashback / 延迟从库 |
| 单表误 DROP | 全库恢复到临时实例 → 导出表 |

恢复能力是 MySQL SRE **核心 KPI**。
