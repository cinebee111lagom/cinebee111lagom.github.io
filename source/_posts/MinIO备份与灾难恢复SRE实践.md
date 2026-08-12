---
title: MinIO 备份与灾难恢复 SRE 实践
date: 2026-09-02 10:30:00
tags:
  - MinIO
  - SRE
  - 备份
categories:
  - MinIO SRE
---

MinIO EC **不是备份**，仍需 **跨集群复制 + 配置备份**。

## DR 策略

| 层级 | 方式 | RPO |
|------|------|-----|
| 桶级复制 | active-active/DR | 分钟 |
| 站点复制 | 多站点元数据 | 分钟 |
| mc mirror | 定时全量/增量 | 小时 |
| 配置 | export policy/user | - |

## 桶级复制（生产 DR）

```bash
mc replicate add prod/assets --remote-bucket dr/assets \
  --priority 1 --replicate "delete,delete-marker,existing-objects"
mc replicate status prod/assets
```

## 配置备份

```bash
mc admin config export prod > minio-config-$(date +%F).json
mc admin policy list prod
mc admin user list prod > users-$(date +%F).txt
```

存 **加密对象仓或 vault**，勿明文 Git。

## 恢复演练

```
1. DR 集群独立可用
2. 抽样 bucket 对象数 md5 对比
3. 模拟 prod 全挂，应用切 DR endpoint
4. 记录 RTO
```

目标：**半年一次** 完整演练。

## Velero 场景

MinIO 作备份目标时，DR = **第二 MinIO + mirror Velero bucket**。

## 反模式

- 同集群「备份」桶
- 从未切 DR 演练
- replication 无监控 lag

3-2-1：**生产 + 异地复制 + 离线抽样**。
