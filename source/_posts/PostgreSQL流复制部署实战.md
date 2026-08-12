---
title: PostgreSQL 流复制部署实战
date: 2026-08-15 09:30:00
tags:
  - PostgreSQL
  - 流复制
categories:
  - PostgreSQL SRE
---

流复制（Streaming Replication）是 PostgreSQL HA 与读写分离的基础。

## 主库配置（postgresql.conf）

```ini
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
hot_standby = on
archive_mode = on
archive_command = 'test ! -f /wal_archive/%f && cp %p /wal_archive/%f'
```

## pg_hba.conf 允许复制

```
host replication repl 10.0.1.0/24 scram-sha-256
```

## 创建复制用户

```sql
CREATE USER repl WITH REPLICATION PASSWORD 'repl_password';
```

## 从库初始化（pg_basebackup）

```bash
pg_basebackup -h 10.0.1.10 -U repl -D /var/lib/postgresql/data \
  -Fp -Xs -P -R
```

`-R` 自动生成 `standby.signal` 与 `primary_conninfo`。

## 从库关键配置

```ini
hot_standby = on
hot_standby_feedback = on
max_standby_streaming_delay = 30s
```

## 验证复制状态

```sql
-- 主库
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn
FROM pg_stat_replication;

-- 从库
SELECT pg_is_in_recovery(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
```

## 部署检查清单

- [ ] `wal_level = replica` 或以上
- [ ] 复制槽（可选但推荐，防 WAL 被删）
- [ ] 从库只读（默认 recovery 模式）
- [ ] 监控复制延迟（`replay_lag`）
- [ ] 备份与归档路径独立磁盘

## 延迟排查

- 大事务、长查询阻塞 replay
- 从库 I/O 弱于主库
- 网络带宽不足
- 未开 `hot_standby_feedback` 导致 vacuum 冲突

流复制本身不自动切换，需 Patroni / repmgr / 人工 failover。
