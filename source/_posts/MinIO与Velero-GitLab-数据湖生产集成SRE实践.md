---
title: MinIO 与 Velero、GitLab、数据湖生产集成 SRE 实践
date: 2026-09-02 13:45:00
tags:
  - MinIO
  - SRE
  - 集成
categories:
  - MinIO SRE
---

MinIO 常作 **K8s 备份、CI 制品、数据湖** 的统一 S3 底座。

## Velero（K8s 备份）

```yaml
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: default
spec:
  provider: aws
  objectStorage:
    bucket: velero-backup
  config:
    region: minio
    s3ForcePathStyle: "true"
    s3Url: https://s3.internal:9000
    publicUrl: https://s3.internal:9000
```

SRE 职责：**bucket 容量、lifecycle、repl 到 DR、restore 演练**。

## GitLab / CI 制品

```ruby
# gitlab.rb 对象存储
gitlab_rails['object_store']['enabled'] = true
gitlab_rails['object_store']['connection'] = {
  'provider' => 'AWS',
  'endpoint' => 'https://s3.internal:9000',
  ...
}
```

独立 bucket + 只写 Policy + 监控容量增长。

## 数据湖（Spark/Iceberg）

```
s3a://datalake/warehouse/
endpoint + path-style + access-key
```

大对象顺序读，**EC + 25G 网络**；冷热分层 lifecycle。

## 联合监控

| 消费者 | 指标 |
|--------|------|
| Velero | backup fail rate |
| GitLab | object store error |
| MinIO | bucket 容量、5xx |

## 故障分工

```
应用报 S3 错 → 先 MinIO health
MinIO OK → 查消费者 credential/endpoint
MinIO ERR → 存储 SRE Runbook
```

## 反模式

- 备份/制品/业务共 bucket 无 prefix 隔离
- Velero 无 DR bucket
- 数据湖无 lifecycle 无限增长

---

**MinIO SRE 系列 20 篇**完结。建议与 **MinIO 新手入门**、**Ceph SRE** 对照阅读。
