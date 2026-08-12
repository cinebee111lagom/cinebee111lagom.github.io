---
title: PostgreSQL 多机房容灾与读写切换
date: 2026-08-15 13:15:00
tags:
  - PostgreSQL
  - 容灾
categories:
  - PostgreSQL SRE
---

多机房部署目标：区域故障时 RPO/RTO 可控，读写切换可演练。

## 拓扑

```
Region A（Primary + Patroni + etcd）
    │ 异步/同步流复制
Region B（Standby + Patroni + etcd 副本或独立 DCS）
    │ WAL 归档 → 对象存储（跨区域）
Region C（可选 DR 只读 / 延迟 standby）
```

## 复制模式选择

| 模式 | RPO | 跨机房 |
|------|-----|--------|
| 异步 | 秒~分钟 | 常用，写延迟低 |
| sync remote_apply | 0 | 写延迟高，跨 RTT 敏感 |
| 逻辑复制 | 秒级 | 跨版本、 selective |

## Patroni 跨 Region

- etcd 建议每 Region 独立集群，Patroni 用 **sync standby** 标签
- 或 Region B 为独立集群 + 逻辑复制（避免脑裂）

## 切换流程

### 计划内（Region A 维护）

1. 提升 Region B standby 为 primary
2. 更新 PgBouncer/HAProxy/DNS
3. 应用重连验证
4. Region A 恢复后作为新 standby rejoin

### 故障切换

```bash
patronictl failover pg-cluster --candidate pg-b1
# 或 Patroni 自动 failover（同 Region）
```

跨 Region 通常需 **人工确认** 防脑裂。

## 对象存储 WAL 归档

```ini
archive_command = 'aws s3 cp %p s3://dr-bucket/wal/%f --region us-west-2'
```

Region A 全毁时，从 S3 WAL + base backup 在 B 做 PITR。

## 读写分离跨 Region

- 读流量走本地 standby（延迟读）
- 写必须走 primary Region
- 避免跨洋同步复制拖慢全局写

## 检查清单

- [ ] RPO/RTO 文档化并季度演练
- [ ] 跨区域网络带宽 ≥ WAL 产生速率
- [ ] 切换 Runbook（DNS TTL ≤ 60s）
- [ ] 应用连接串支持快速切换
- [ ] 脑裂防护（fencing / 人工 gate）

容灾不是备份替代品，**切换必须演练**。
