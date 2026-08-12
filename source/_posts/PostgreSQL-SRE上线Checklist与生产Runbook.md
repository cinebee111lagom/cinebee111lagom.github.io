---
title: PostgreSQL SRE 上线 Checklist 与生产 Runbook
date: 2026-08-15 13:45:00
tags:
  - PostgreSQL
  - SRE
  - Runbook
categories:
  - PostgreSQL SRE
---

## 上线 Checklist

### 架构

- [ ] 架构文档已评审（流复制/Patroni/Citus）
- [ ] HA 方案明确（Patroni + HAProxy + PgBouncer）
- [ ] 容量压测：QPS、连接数、磁盘与 WAL 增长

### 配置

- [ ] 生产参数基线已应用
- [ ] wal_level = replica，归档开启
- [ ] max_connections 与 PgBouncer 池大小联动
- [ ] pg_stat_statements 已启用
- [ ] autovacuum 参数已调优
- [ ] 慢查询日志 / auto_explain 开启

### 安全

- [ ] 最小权限角色，无 superuser 远程
- [ ] scram-sha-256 + SSL
- [ ] pg_hba 无 trust / 0.0.0.0/0
- [ ] 网络 ACL，无公网 5432

### 备份

- [ ] pg_basebackup / pgBackRest 定时 + 异地
- [ ] WAL 归档连续，满足 PITR
- [ ] 3 个月内 PITR 演练成功

### 监控

- [ ] postgres_exporter + Prometheus
- [ ] Grafana Dashboard
- [ ] P0/P1 告警 + Runbook 链接
- [ ] 复制延迟、连接数、磁盘、deadlock 监控

---

## 日常 Runbook

### 主库不可写

```bash
systemctl status postgresql
tail -100 /var/log/postgresql/postgresql-*.log
df -h
patronictl list
psql -c "SELECT pg_is_in_recovery();"
```

### 复制中断

```sql
SELECT * FROM pg_stat_replication;
SELECT slot_name, active, restart_lsn FROM pg_replication_slots;
-- 必要时 patronictl reinit
```

### 连接打满

```sql
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
-- 查 idle in transaction
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE ...;
```

### 磁盘告警

- 检查 WAL 未归档堆积
- 检查 `pg_wal` 目录大小
- 扩容或清理历史分区
- 禁止盲目 `rm` WAL

### 紧急切主

1. `patronictl failover pg-cluster --candidate <node>`
2. 更新 HAProxy / PgBouncer / DNS
3. 验证 `pg_is_in_recovery() = false` on new primary
4. 应用读写验证
5. 旧 primary rejoin 为 standby

### VACUUM 滞后

```sql
SELECT relname, n_dead_tup, last_autovacuum FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;
-- 终止长事务后手动 VACUUM ANALYZE
```

---

**PostgreSQL SRE 系列 20 篇**完结，涵盖部署、HA、备份、监控、安全、K8s、分片、调优、DDL、容灾与演练。建议配合 **MySQL SRE**、**Redis SRE** 系列对照阅读，构建完整存储层 SRE 知识体系。
