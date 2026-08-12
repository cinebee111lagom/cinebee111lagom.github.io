---
title: MinIO 审计日志与合规
date: 2026-09-02 13:15:00
tags:
  - MinIO
  - SRE
  - 合规
categories:
  - MinIO SRE
---

合规要求 **对象访问可追溯、策略变更可审计**。

## 审计配置

```bash
mc admin config set alias audit_webhook:primary \
  enable=on \
  endpoint=https://siem.example.com/minio-audit \
  auth_token=xxx

mc admin service restart alias
```

## 记录内容

- PutObject/GetObject/DeleteObject
- BucketPolicy 变更
- Login/Admin API
- IAM 用户创建

## 合规映射

| 要求 | 措施 |
|------|------|
| 访问审计 | audit webhook |
| 静态加密 | SSE-S3/KMS |
| 保留 | Object Lock compliance |
| 最小权限 | IAM Policy |
| 保留期 | lifecycle + legal hold |

## Object Lock 合规桶

```bash
mc retention set --default compliance 7y alias/legal-records
```

## SIEM 告警

- 匿名策略启用
- root 凭证使用
- 大量 DeleteObject
- 异常 IP ListBucket

## 反模式

- 无审计仅 bucket 日志
- compliance lock 测试桶
- 审计 endpoint 无 TLS

纳入 **等保/SOC2** 控制矩阵。
