---
title: GitLab PostgreSQL 与 Redis 生产运维
date: 2026-08-29 12:15:00
tags:
  - GitLab
  - SRE
  - PostgreSQL
categories:
  - GitLab SRE
---

GitLab 元数据在 **PostgreSQL**，队列/缓存在 **Redis**，二者故障影响全站。

## PostgreSQL

### 生产要求

| 项 | 建议 |
|----|------|
| HA | Patroni 3 节点 |
| 版本 | 符合 GitLab 官方兼容矩阵 |
| 连接 | PgBouncer（可选） |
| 备份 | pg_basebackup + WAL |

### 监控

```yaml
- alert: GitLabPGConnectionsHigh
  expr: pg_stat_activity_count / pg_settings_max_connections > 0.85
  for: 10m

- alert: GitLabPGReplicationLag
  expr: pg_replication_lag > 300
  for: 5m
```

### 维护

```bash
gitlab-rake db:migrate:status
gitlab-rake gitlab:db:decompose  # 大版本升级后
```

## Redis

| 用途 | 说明 |
|------|------|
| Sidekiq 队列 | 关键，需 HA |
| Cache | 可重建 |
| ActionCable | 会话 |

```ruby
redis['enable'] = true
redis['ha'] = true
redis['master_name'] = 'gitlab-redis'
```

Sentinel 或 Redis Cluster，**禁止单点**。

## 故障 Runbook

| 故障 | 动作 |
|------|------|
| PG 主挂 | Patroni failover |
| Redis 主挂 | Sentinel promote |
| 连接耗尽 | 查 long query、重启 sidekiq |

## 反模式

- 内置 PostgreSQL 跑大生产
- Redis 无持久化无 HA
- 不做 PG vacuum/autovacuum 监控

PG/Redis 变更走 **数据库 SRE 联合变更单**。
