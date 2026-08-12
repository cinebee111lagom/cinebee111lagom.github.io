---
title: MySQL 备份策略：mysqldump、xtrabackup 与 binlog
date: 2026-08-14 10:15:00
tags:
  - MySQL
  - 备份
categories:
  - MySQL SRE
---

备份是 SRE 最后的防线，需组合**逻辑备份、物理备份、binlog**。

## 三种方式

| 方式 | 速度 | 恢复 | 适用 |
|------|------|------|------|
| mysqldump | 慢 | 逻辑 SQL | 小库、跨版本 |
| xtrabackup | 快 | 物理拷贝 | 大库生产 |
| binlog | 增量 | PITR | 与全量配合 |

## mysqldump

```bash
mysqldump -u backup -p --single-transaction --master-data=2 \
  --routines --triggers --databases mydb \
  | gzip > mydb-$(date +%F).sql.gz
```

`--single-transaction` 对 InnoDB 不锁表。

## Percona XtraBackup

```bash
xtrabackup --backup --target-dir=/backup/full-$(date +%F)
xtrabackup --prepare --target-dir=/backup/full-$(date +%F)
```

从库备份不影响主库（`--slave-info`）。

## binlog

```ini
log_bin = mysql-bin
binlog_expire_logs_seconds = 604800   # 7 天
binlog_format = ROW
```

## 保留策略

- 全量：日备 7 天 + 周备 4 周
- binlog：至少覆盖两次全量间隔
- 异地：S3/OSS 加密存储

## 验证

**未经验证的备份等于没有备份**——每月恢复演练到测试实例。
