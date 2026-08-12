---
title: MinIO 用户与访问策略入门
date: 2026-09-01 10:30:00
tags:
  - MinIO
  - 权限
  - 入门
categories:
  - MinIO 新手入门
---

MinIO 用 **用户 + Policy** 控制谁能访问哪些 Bucket/Object。

## 创建用户

```bash
mc admin user add local appuser 'AppSecret123!'
mc admin user list local
```

## 内置 Policy

| Policy | 权限 |
|--------|------|
| readwrite | 读写所有 |
| readonly | 只读 |
| writeonly | 只写 |
| consoleAdmin | 管理 Console |

```bash
mc admin policy attach local readwrite --user appuser
```

## 自定义 Policy（JSON）

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::my-app-assets",
        "arn:aws:s3:::my-app-assets/*"
      ]
    }
  ]
}
```

```bash
mc admin policy create local my-app-policy policy.json
mc admin policy attach local my-app-policy --user appuser
```

## 服务账号（推荐应用使用）

```bash
mc admin user svcacct add local appuser --access-key SVCKEY123 --secret-key SVCSECRET456
```

应用用 **svcacct**，不直接用 root。

## 最小权限原则

```
备份程序 → 仅 PutObject 到 backup bucket
CDN 源站 → 仅 GetObject
管理员   → consoleAdmin（少数人）
```

## 反模式

- 应用使用 MINIO_ROOT_USER
- readwrite 给所有用户
- Policy Resource 用 `*` 无必要

下一篇：**上传下载与 presigned URL**。
