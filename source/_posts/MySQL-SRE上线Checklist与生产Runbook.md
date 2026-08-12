---
title: MySQL SRE 上线 Checklist 与生产 Runbook
date: 2026-08-14 13:45:00
tags:
  - MySQL
  - SRE
  - Runbook
categories:
  - MySQL SRE
---

## 上线 Checklist

### 架构

- [ ] 架构文档已评审（主从/MGR/分片）
- [ ] HA 方案明确（Orchestrator/MGR/Proxy）
- [ ] 容量压测：QPS、连接数、磁盘增长

### 配置

- [ ] InnoDB 参数基线已应用
- [ ] GTID + ROW binlog 开启
- [ ] max_connections 与连接池联动
- [ ] 字符集 utf8mb4
- [ ] 慢日志开启

### 安全

- [ ] 最小权限账号，无 root 远程
- [ ] SSL（若要求）
- [ ] 网络 ACL，无公网 3306

### 备份

- [ ] 全量备份 cron + 异地存储
- [ ] binlog 保留满足 PITR
- [ ] 3 个月内恢复演练成功

### 监控

- [ ] mysqld_exporter + Prometheus
- [ ] Grafana Dashboard
- [ ] P0/P1 告警 + Runbook 链接
- [ ] 复制延迟监控

---

## 日常 Runbook

### 主库不可写

```bash
systemctl status mysqld
tail -100 /var/log/mysql/error.log
df -h
SHOW ENGINE INNODB STATUS\G
```

### 复制中断

```sql
SHOW SLAVE STATUS\G
-- Last_SQL_Error 定位
-- 谨慎 SET GLOBAL SQL_SLAVE_SKIP_COUNTER（非 GTID）
```

### 连接打满

```sql
SELECT * FROM information_schema.processlist ORDER BY time DESC;
-- KILL 长期 Sleep；协调应用扩池/泄漏修复
```

### 磁盘告警

- 清理 binlog（确认备份后 `PURGE BINARY LOGS`）
- 归档历史表
- 扩容磁盘

### 紧急切主

1. Orchestrator UI / `orchestrator-client` 触发
2. 或 MGR 自动 / 手动 `SELECT group_replication_set_as_primary()`
3. 更新 ProxySQL / DNS
4. 验证应用读写

---

**MySQL SRE 系列 20 篇**完结，涵盖部署、HA、备份、监控、安全、K8s、分片、调优、DDL、容灾与演练。建议配合 **Redis SRE** 系列对照阅读，构建完整存储层 SRE 知识体系。
