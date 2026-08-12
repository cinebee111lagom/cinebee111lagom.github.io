---
title: Redis 性能基准测试与容量规划
date: 2026-08-13 17:00:00
tags:
  - Redis
  - 性能
categories:
  - Redis SRE
---

上线前用 **redis-benchmark** 与业务压测确定容量，避免生产首日打挂。

## redis-benchmark

```bash
redis-benchmark -h 10.0.1.10 -a pass -c 50 -n 100000 -t get,set
redis-benchmark -h 10.0.1.10 -a pass -c 100 -n 500000 -d 256 -t set,get
```

关注：QPS、P99 延迟、CPU 使用率。

## 容量规划公式

```
峰值 QPS × 平均 value 大小 ≈ 网络带宽需求
key 数量 × 平均大小 × 1.3 ≈ 内存需求
连接数 = 应用实例数 × 每实例连接池大小
```

## 压测场景

| 场景 | 命令 mix |
|------|----------|
| 纯缓存 | 80% GET, 20% SET |
| 会话 | SETEX + GET |
| 队列 | LPUSH + BRPOP |
| 计数 | INCR |

## 瓶颈识别

| 现象 | 瓶颈 |
|------|------|
| CPU 100% 单核 | Redis 单线程，需分片 |
| 网络打满 | 大 value、跨 AZ |
| 延迟尖刺 | fork、AOF rewrite、大 key |

## 上线前 checklist

- [ ] 峰值 QPS 下 P99 < SLA
- [ ] 内存使用率 < 70%
- [ ] 连接数 < maxclients 60%
- [ ] 主从延迟 < 1MB offset

基准数据写入**容量文档**，扩容有据可依。
