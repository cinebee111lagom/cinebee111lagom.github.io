---
title: PostgreSQL 恢复与 PITR 点时间恢复
date: 2026-08-15 10:30:00
tags:
  - PostgreSQL
  - PITR
  - 恢复
categories:
  - PostgreSQL SRE
---

PITR（Point-In-Time Recovery）通过基础备份 + WAL 归档恢复到任意时间点。

## 恢复流程概览

```
1. 停止 PostgreSQL
2. 清空 data 目录
3. 解压 pg_basebackup
4. 配置 recovery（restore_command + recovery_target）
5. 启动并 replay WAL
6. 提升为 primary（promote）
```

## recovery 配置（postgresql.conf / recovery.signal）

```ini
restore_command = 'cp /wal_archive/%f %p'
recovery_target_time = '2026-08-15 10:00:00+08'
recovery_target_action = promote
```

PostgreSQL 12+ 使用 `recovery.signal` 文件触发 recovery 模式。

## 误删表恢复（单库）

```bash
# 1. 恢复到误操作前的时间点（独立实例）
# 2. pg_dump 导出目标表
pg_dump -h recovery-host -U postgres -t orders -Fc mydb > orders.dump

# 3. 导入生产
pg_restore -h prod -U app -d mydb orders.dump
```

## pgBackRest PITR

```bash
pgbackrest --stanza=main restore \
  --type=time --target='2026-08-15 10:00:00+08' \
  --target-action=promote
```

## RPO/RTO 验证

| 场景 | 目标 | 验证方式 |
|------|------|----------|
| 全库崩溃 | RTO < 30min | 季度演练 |
| 误 DROP | RPO < 5min | WAL 归档延迟监控 |
| 机房故障 | RTO < 1h | 跨 Region 副本切换 |

## 演练 Checklist

- [ ] 在隔离环境恢复，禁止直接覆盖生产
- [ ] 记录恢复耗时写入 Runbook
- [ ] 验证数据一致性（行数、checksum）
- [ ] 恢复后 `pg_promote()` 或删除 recovery 信号

## 常见坑

- WAL 归档 gap → PITR 失败，需连续 WAL
- 时区：`recovery_target_time` 带时区
- 大库恢复：用 `-j` 并行 pg_restore 或 pgBackRest

每季度至少一次 PITR 演练，并保留演练报告。
