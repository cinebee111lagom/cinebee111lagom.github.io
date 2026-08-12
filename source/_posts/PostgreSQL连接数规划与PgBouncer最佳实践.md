---
title: PostgreSQL 连接数规划与 PgBouncer 最佳实践
date: 2026-08-15 11:30:00
tags:
  - PostgreSQL
  - PgBouncer
  - 连接池
categories:
  - PostgreSQL SRE
---

PostgreSQL 每个连接是独立进程，连接过多会拖垮 CPU 与内存，**PgBouncer** 是生产标配。

## 连接数规划

```
max_connections ≈ (CPU 核数 × 2) + 余量
实际应用连接 → PgBouncer → PostgreSQL（少量后端连接）
```

| 场景 | 建议 |
|------|------|
| 微服务 50+ 实例 | 必须 PgBouncer |
| OLTP | pool_mode = transaction |
| 长事务/ prepared stmt 多 | pool_mode = session |

## PgBouncer 配置（pgbouncer.ini）

```ini
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
default_pool_size = 50
max_client_conn = 1000
reserve_pool_size = 10
server_reset_query = DISCARD ALL
```

## 监控

```sql
SHOW POOLS;
SHOW STATS;
SHOW CLIENTS;
```

Prometheus：`pgbouncer_exporter` 采集 `pgbouncer_pools_*`。

## 应用侧注意

- **transaction 模式**：勿在事务内用临时表、 advisory lock 跨请求
- 使用 **prepared statements** 时确认 PgBouncer 版本支持
- 连接泄漏：设置 `idle_in_transaction_session_timeout`

```ini
idle_in_transaction_session_timeout = 60000  # ms
statement_timeout = 30000
```

## 排查连接打满

```sql
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
SELECT pid, usename, application_name, state, query_start, query
FROM pg_stat_activity WHERE state = 'idle in transaction';
```

## 检查清单

- [ ] 应用连接 PgBouncer 而非直连 PG
- [ ] `max_client_conn` 与 `default_pool_size` 合理
- [ ] 监控 waiting clients
- [ ] 设置 statement/idle 超时
- [ ] 压测验证池大小

**公式**：应用总连接可以上千，PostgreSQL 后端连接控制在 100~200。
