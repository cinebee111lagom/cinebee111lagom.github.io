---
title: Redis 监控体系：Prometheus 与 Grafana
date: 2026-08-13 16:15:00
tags:
  - Redis
  - 监控
  - Prometheus
categories:
  - Redis SRE
---

没有监控的 Redis 等于盲飞。Prometheus + redis_exporter 是业界标准组合。

## 部署 redis_exporter

```bash
docker run -d --net=host \
  oliver006/redis_exporter \
  --redis.addr=redis://10.0.1.10:6379 \
  --redis.password=pass
```

K8s 使用 ServiceMonitor 抓取 `:9121/metrics`。

## 核心指标

| 指标 | 含义 |
|------|------|
| `redis_up` | 实例存活 |
| `redis_memory_used_bytes` | 已用内存 |
| `redis_connected_clients` | 连接数 |
| `redis_commands_processed_total` | QPS |
| `redis_keyspace_hits_total` / misses | 命中率 |
| `redis_replication_master_link_up` | 主从链路 |
| `redis_connected_slaves` | 从库数 |

## 命中率

```
hit_rate = hits / (hits + misses)
```

低于 90% 需排查：TTL 过短、缓存穿透、容量不足。

## Grafana Dashboard

- 官方 Dashboard ID：763（Redis Dashboard for Prometheus）
- 分屏：内存、QPS、延迟、复制、慢查询

## 日志

```conf
slowlog-log-slower-than 10000   # 10ms
slowlog-max-len 128
```

Loki/ELK 采集 Redis 日志 + 慢查询导出。

监控覆盖 **四个黄金信号**：延迟、流量、错误、饱和度。
