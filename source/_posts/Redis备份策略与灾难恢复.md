---
title: Redis 备份策略与灾难恢复
date: 2026-08-13 16:45:00
tags:
  - Redis
  - 备份
  - DR
categories:
  - Redis SRE
---

Redis 备份不是可选——误删 FLUSHALL、机房故障都需要恢复路径。

## 备份方式

| 方式 | RPO | 适用 |
|------|-----|------|
| RDB 定时 BGSAVE | 分钟~小时 | 全量基线 |
| AOF 文件同步 | ≤1s | 增量 |
| 磁盘快照（云） | 小时 | 基础设施级 |
| 主从 + 从库备份 | 低 | 不影响主库 |

## 自动化脚本

```bash
#!/bin/bash
BACKUP_DIR=/backup/redis/$(date +%F)
mkdir -p $BACKUP_DIR
redis-cli -a $PASS BGSAVE
while [ "$(redis-cli -a $PASS LASTSAVE)" = "$(redis-cli -a $PASS LASTSAVE)" ]; do sleep 1; done
cp /var/lib/redis/dump.rdb $BACKUP_DIR/
aws s3 cp $BACKUP_DIR s3://my-bucket/redis/ --recursive
```

## 恢复流程

1. 停止目标实例
2. 替换 `dump.rdb` 或 `appendonly.aof`
3. 启动 Redis，检查 `redis-cli DBSIZE`
4. 业务验证抽样 key

## 跨地域 DR

- 异步复制到 DR 站点从库（延迟接受）
- 或定时 S3 备份 + DR 区域恢复演练
- RTO/RPO 写入 SLA 文档

## 保留策略

- 日备保留 7 天
- 周备保留 4 周
- 月备保留 12 个月

**每季度 DR 演练**一次，实测恢复耗时。
