---
title: MinIO 桶级复制与站点复制生产实践
date: 2026-09-02 11:45:00
tags:
  - MinIO
  - SRE
  - 复制
categories:
  - MinIO SRE
---

生产 DR 依赖 **Bucket Replication** 或 **Site Replication**，需监控 lag。

## 桶级复制配置

```bash
mc replicate add prod/assets \
  --remote-bucket dr/assets \
  --remote-bucket-region us-east-1 \
  --priority 1 \
  --replicate "delete,delete-marker,existing-objects,metadata-sync"

mc replicate update prod/assets --id xxx --health-check-period 60s
```

## 多目标优先级

```
priority 1 → DR 同城
priority 2 → DR 异地
```

## 站点复制（多集群）

```bash
mc admin replicate add site-prod site-dr
mc admin replicate info site-prod
```

同步 **IAM、bucket 元数据**（视版本/许可证）。

## 监控

```bash
mc replicate backlog prod/assets
mc admin replicate status site-prod
```

告警：`replication lag > 15min`。

## 故障切换

```
1. 确认 prod 不可恢复或只读
2. DNS/LB 切 dr endpoint
3. 应用改 endpoint（或统一 DNS）
4. 验证读写
5. 事后 mc mirror 反向或重建复制
```

## 反模式

- 双向复制 + 应用双写无冲突策略
- 无 backlog 监控
- DR 桶 Policy 不一致 403

复制规则 **Infrastructure as Code**（mc 脚本 + Git）。
