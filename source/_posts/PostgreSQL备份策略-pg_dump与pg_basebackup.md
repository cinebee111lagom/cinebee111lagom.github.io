---
title: PostgreSQL 备份策略：pg_dump 与 pg_basebackup
date: 2026-08-15 10:15:00
tags:
  - PostgreSQL
  - 备份
categories:
  - PostgreSQL SRE
---

PostgreSQL 备份分逻辑备份（pg_dump）与物理备份（pg_basebackup），生产需两者结合。

## 逻辑备份（pg_dump）

```bash
# 单库自定义格式（可并行恢复）
pg_dump -h localhost -U app -Fc -f backup_$(date +%Y%m%d).dump mydb

# 全库 SQL（小库）
pg_dumpall -h localhost -U postgres -f all_$(date +%Y%m%d).sql
```

优点：跨版本、可选择对象；缺点：大数据库慢、恢复慢。

## 物理备份（pg_basebackup）

```bash
pg_basebackup -h 10.0.1.10 -U repl -D /backup/base/$(date +%Y%m%d) \
  -Ft -z -P -X stream
```

- `-X stream`：同时流式拉 WAL
- 适合 TB 级快速恢复

## WAL 归档（PITR 基础）

```ini
archive_mode = on
archive_command = 'aws s3 cp %p s3://mybucket/wal/%f'
# 或 rsync / cp 到 NFS
```

## 备份策略参考

| 类型 | 频率 | 保留 | 用途 |
|------|------|------|------|
| pg_basebackup | 每日 | 7~14 天 | 全量物理恢复 |
| WAL 归档 | 实时 | 7~30 天 | PITR |
| pg_dump | 每周 | 90 天 | 逻辑恢复、跨版本迁移 |
| 异地副本 | 实时 | — | 容灾 |

## pgBackRest / Barman（推荐生产）

```ini
# pgBackRest 示例
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=2

[main]
pg1-path=/var/lib/postgresql/data
```

支持增量、并行、校验、S3 后端。

## 检查清单

- [ ] 备份脚本 cron + 失败告警
- [ ] 备份文件加密（at-rest）
- [ ] 异地存储（跨 AZ/Region）
- [ ] 定期恢复演练（见 PITR 篇）
- [ ] 监控 WAL 归档延迟

**3-2-1 原则**：3 份副本、2 种介质、1 份异地。
