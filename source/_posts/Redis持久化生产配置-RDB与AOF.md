---
title: Redis 持久化生产配置：RDB 与 AOF
date: 2026-08-13 15:15:00
tags:
  - Redis
  - 持久化
categories:
  - Redis SRE
---

持久化决定 **RPO**。SRE 必须根据业务容忍度配置 RDB / AOF。

## RDB（快照）

```conf
save 900 1
save 300 10
save 60 10000
dbfilename dump.rdb
dir /var/lib/redis
```

| 优点 | 缺点 |
|------|------|
| 恢复快 | fork 时可能阻塞 |
| 文件紧凑 | 两次快照间可能丢数据 |

## AOF（追加日志）

```conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec    # 生产推荐
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-use-rdb-preamble yes   # Redis 4+ 混合持久化
```

| appendfsync | 安全性 | 性能 |
|-------------|--------|------|
| always | 最高 | 最低 |
| everysec | 丢 ≤1s | 推荐 |
| no | 低 | 最高 |

## 生产推荐

**缓存为主、可重建**：可关持久化或仅 RDB  
**会话/队列/核心状态**：AOF everysec + RDB 备份  
**金融级**：AOF always（需评估磁盘 IO）

## 备份脚本

```bash
redis-cli -a pass BGSAVE
cp /var/lib/redis/dump.rdb /backup/redis/dump-$(date +%F).rdb
```

## 恢复演练

- 定期从 RDB/AOF **恢复到测试实例**验证完整性
- 记录恢复耗时（RTO 基线）

持久化配置写进**配置基线**，变更需评审。
