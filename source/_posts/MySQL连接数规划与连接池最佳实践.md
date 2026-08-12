---
title: MySQL 连接数规划与连接池最佳实践
date: 2026-08-14 11:30:00
tags:
  - MySQL
  - 连接池
categories:
  - MySQL SRE
---

MySQL 连接是**昂贵资源**，`Too many connections` 是经典生产故障。

## 容量公式

```
max_connections ≥ Σ(应用实例数 × 每实例池 maxSize) + 管理连接 + 20% 余量
```

典型生产：`max_connections = 2000~5000`（视内存而定，每连接约 256KB~几 MB）。

## 应用连接池（HikariCP）

```yaml
spring.datasource.hikari:
  maximum-pool-size: 20
  minimum-idle: 5
  connection-timeout: 30000
  idle-timeout: 600000
  max-lifetime: 1800000
```

| 原则 | 说明 |
|------|------|
| 池不宜过大 | 每服务 10~50 通常足够 |
| 设 timeout | 防连接泄漏拖死 |
| 同 AZ | 降低 RT |

## 常见错误

- ❌ 每 HTTP 请求 new Connection
- ❌ 100 个微服务各 100 连接 → 打满 MySQL
- ❌ 无 `wait_timeout`，Sleep 连接堆积

## 排查

```sql
SHOW PROCESSLIST;
SELECT user, host, db, command, time, state FROM information_schema.processlist
WHERE command = 'Sleep' ORDER BY time DESC;
```

```sql
KILL <id>;  -- 谨慎批量
```

## Proxy 层

ProxySQL 连接复用（multiplexing）可**减少后端连接数**。

连接数规划需**应用与 DBA 联合评审**，纳入上线 checklist。
