---
title: MinIO 备份与迁移入门
date: 2026-09-01 13:15:00
tags:
  - MinIO
  - 备份
  - 入门
categories:
  - MinIO 新手入门
---

对象存储备份侧重 **跨桶/跨集群复制** 与 **元数据导出**。

## mc mirror 全桶同步

```bash
mc mirror --overwrite local/mybucket remote/mybucket-backup
mc mirror --watch local/mybucket remote/mybucket-backup  # 持续
```

## rclone

```bash
rclone config  # 配置 local minio 与 remote
rclone sync minio:mybucket backup:mybucket --transfers 8
```

## Velero（K8s）

MinIO 作 **备份目标仓**：

```bash
velero backup create full --include-namespaces app
velero restore create --from-backup full
```

## 配置备份

```bash
mc admin config export local > minio-config-backup.json
mc admin policy list local
mc admin user list local > users-backup.txt
```

## 迁移到新集群

```
1. 新集群建同名 bucket + policy
2. mc mirror old/ new/
3. 应用切 endpoint
4. 验证对象数量与抽样 checksum
```

## 3-2-1 原则

```
3 份数据，2 种介质，1 份异地
MinIO 复制 + 离线/云副本
```

## 反模式

- 只复制不验证 restore
- 单集群无 offsite
- mirror 覆盖无版本保护

下一篇：**排查**。
