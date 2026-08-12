---
title: OpenSearch 快照备份与恢复
date: 2026-08-20 10:15:00
tags:
  - OpenSearch
  - 快照
  - 备份
categories:
  - OpenSearch SRE
---

Snapshot 是 OpenSearch **官方备份机制**，增量备份到 S3/HDFS/NFS 仓库。

## 注册快照仓库

```bash
PUT /_snapshot/s3_repo
{
  "type": "s3",
  "settings": {
    "bucket": "opensearch-snapshots",
    "region": "ap-southeast-1",
    "base_path": "prod-cluster"
  }
}
```

需配置 `opensearch.keystore` 添加 S3 凭证（或使用 IAM Role）。

## 创建快照

```bash
# 全集群
PUT /_snapshot/s3_repo/snap-20260820?wait_for_completion=false
{
  "indices": "*",
  "ignore_unavailable": true,
  "include_global_state": true
}

# 单索引
PUT /_snapshot/s3_repo/snap-logs-20260820
{
  "indices": "logs-2026.08.*"
}
```

## 查看与恢复

```bash
GET /_snapshot/s3_repo/_all
GET /_snapshot/s3_repo/snap-20260820/_status

# 恢复（新集群或误删）
POST /_snapshot/s3_repo/snap-20260820/_restore
{
  "indices": "logs-2026.08.20",
  "ignore_unavailable": true,
  "include_global_state": false
}
```

## 快照策略（SM Plugin）

```bash
PUT /_plugins/_sm/policies/daily-snapshot
{
  "description": "Daily snapshot at 2am",
  "creation": {
    "schedule": { "cron": { "expression": "0 2 * * ?", "timezone": "Asia/Shanghai" } }
  },
  "deletion": {
    "schedule": { "cron": { "expression": "0 3 * * ?" } },
    "condition": { "max_age": "30d", "min_count": 7 }
  },
  "snapshot_config": {
    "repository": "s3_repo",
    "indices": "*"
  }
}
```

## RPO/RTO

| 策略 | RPO | RTO |
|------|-----|-----|
| 每日快照 | 24h | 1~4h（视数据量） |
| 每小时快照 | 1h | 同上 |
| CCR 实时复制 | 秒~分钟 | 分钟级切换 |

## 检查清单

- [ ] 快照仓库高可用（S3 跨 AZ）
- [ ] 每日自动快照 + 保留 30 天
- [ ] 季度 restore 演练
- [ ] 监控快照 FAILED 状态
- [ ] 恢复流程 Runbook

**没有 restore 演练的快照等于没有备份**。
