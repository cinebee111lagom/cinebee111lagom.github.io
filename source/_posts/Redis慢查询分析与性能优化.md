---
title: Redis 慢查询分析与性能优化
date: 2026-08-13 17:15:00
tags:
  - Redis
  - 慢查询
categories:
  - Redis SRE
---

Redis 单线程：一条慢命令**阻塞全局**，SRE 必须持续治理慢查询。

## 慢日志配置

```conf
slowlog-log-slower-than 10000   # 微秒，10ms
slowlog-max-len 256
```

```bash
redis-cli SLOWLOG GET 20
redis-cli SLOWLOG LEN
redis-cli SLOWLOG RESET
```

## 常见慢命令

| 命令 | 原因 |
|------|------|
| KEYS * | O(N) 全表扫描 |
| FLUSHALL | 清空所有 DB |
| SUNION 大集合 | 集合过大 |
| HGETALL 大 hash | 字段过多 |
| LRANGE 0 -1 大 list | 一次拉全量 |

## 优化替代

| 避免 | 改用 |
|------|------|
| KEYS pattern | SCAN 游标迭代 |
| 大 HGETALL | HSCAN 或拆分 |
| 大 SMEMBERS | SSCAN |

## 监控集成

redis_exporter 暴露 `redis_slowlog_length`，结合 Loki 解析慢日志。

## Latency 诊断

```bash
redis-cli --latency -h host
redis-cli --latency-history -h host
redis-cli LATENCY DOCTOR
```

## SRE 流程

1. 每周审查 Top 10 慢命令
2. 推动开发改 SCAN / 拆 key
3. 必要时 rename-command 禁用危险命令

慢查询清零是 Redis **稳定低延迟**的基本功。
