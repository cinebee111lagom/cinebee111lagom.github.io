---
title: MinIO Bucket 创建与管理入门
date: 2026-09-01 10:15:00
tags:
  - MinIO
  - Bucket
  - 入门
categories:
  - MinIO 新手入门
---

**Bucket** 是对象容器，命名全局唯一（单集群内）。

## 创建 Bucket

```bash
mc mb local/my-app-assets
mc mb local/logs-prod

# 带 region（可选）
mc mb --region cn-east-1 local/mybucket
```

Console：**Buckets → Create Bucket**

## 命名规范

| 规则 | 示例 |
|------|------|
| 3~63 字符 | `my-bucket-01` |
| 小写字母、数字、连字符 | ✅ `app-logs` |
| 勿像 IP | ❌ `192.168.1.1` |

## 常用配置

```bash
# 版本控制（见专题篇）
mc version enable local/mybucket

# 配额
mc quota set local/mybucket --size 100GB

# 标签
mc tag set local/mybucket/file.txt "env=prod&team=backend"
```

## 列出对象

```bash
mc ls local/mybucket
mc ls --recursive local/mybucket/prefix/
```

## 公共读（谨慎）

```bash
mc anonymous set download local/public-assets
# 生产建议用 presigned URL 而非 public bucket
```

## Bucket 组织建议

```
tenant-a-prod
tenant-a-dev
backup-velero
ml-datasets-2024
```

按 **租户/环境/用途** 分桶，便于 Policy 与生命周期。

## 反模式

- 一个 bucket 混所有业务
- public 桶放敏感数据
- bucket 名无规范难治理

下一篇：**用户与访问策略**。
