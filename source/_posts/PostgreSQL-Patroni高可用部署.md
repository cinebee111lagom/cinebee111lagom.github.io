---
title: PostgreSQL Patroni 高可用部署
date: 2026-08-15 09:45:00
tags:
  - PostgreSQL
  - Patroni
  - 高可用
categories:
  - PostgreSQL SRE
---

Patroni 通过 DCS（etcd/Consul/ZooKeeper）管理 PostgreSQL 集群 leader 选举与 failover。

## 架构

```
App → HAProxy/PgBouncer → Patroni 管理的 Primary
                       → Standby（只读，可选）
etcd 集群（3 节点）← Patroni 心跳与锁
```

## Patroni 配置示例（patroni.yml）

```yaml
scope: pg-cluster
name: pg1

restapi:
  listen: 0.0.0.0:8008

etcd3:
  hosts: 10.0.1.21:2379,10.0.1.22:2379,10.0.1.23:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    synchronous_mode: false
  initdb:
    - encoding: UTF8
    - locale: en_US.UTF-8
  pg_hba:
    - host replication repl 0.0.0.0/0 scram-sha-256
    - host all all 0.0.0.0/0 scram-sha-256

postgresql:
  listen: 0.0.0.0:5432
  data_dir: /var/lib/postgresql/data
  authentication:
    replication:
      username: repl
      password: repl_password
    superuser:
      username: postgres
      password: postgres_password
  parameters:
    wal_level: replica
    hot_standby: "on"
```

## HAProxy 读写分离

```ini
listen pg_write
  bind *:5000
  option httpchk GET /primary
  http-check expect status 200
  default-server inter 3s fall 3 rise 2
  server pg1 10.0.1.11:5432 check port 8008
  server pg2 10.0.1.12:5432 check port 8008 backup

listen pg_read
  bind *:5001
  option httpchk GET /replica
  balance roundrobin
  server pg1 10.0.1.11:5432 check port 8008
  server pg2 10.0.1.12:5432 check port 8008
```

Patroni REST API：`/primary`、`/replica`、`/health`。

## 常用运维命令

```bash
patronictl -c /etc/patroni/patroni.yml list
patronictl -c /etc/patroni/patroni.yml failover pg-cluster
patronictl -c /etc/patroni/patroni.yml reinit pg-cluster pg2
```

## 同步复制（可选）

```yaml
synchronous_mode: true
synchronous_mode_strict: false
synchronous_node_count: 1
```

RPO=0，但写性能下降；适合金融等强一致场景。

## 检查清单

- [ ] etcd 3 节点独立部署
- [ ] `maximum_lag_on_failover` 防止脏切换
- [ ] HAProxy health check 指向 Patroni REST
- [ ] 定期 failover 演练
- [ ] 监控 `patroni_*` 指标

Patroni 是 PostgreSQL 生产 HA 的事实标准。
