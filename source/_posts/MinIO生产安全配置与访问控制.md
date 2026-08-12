---
title: MinIO 生产安全配置与访问控制
date: 2026-09-02 11:00:00
tags:
  - MinIO
  - SRE
  - 安全
categories:
  - MinIO SRE
---

对象存储泄露影响面大，**IAM + TLS + 网络** 是生产底线。

## 身份

| 实践 | 说明 |
|------|------|
| 禁用 root 日常使用 | 仅 break-glass |
| 应用 svcacct | 最小 Policy |
| 密钥轮换 | 90 天 |
| STS/临时凭证 | 短期上传 |

## Policy 示例（只写备份桶）

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::backup-velero",
      "arn:aws:s3:::backup-velero/*"
    ]
  }]
}
```

## 加密

| 层 | 方式 |
|----|------|
| 传输 | TLS 1.2+ |
| 静态 | SSE-S3 / SSE-KMS（MinIO KMS） |
| 磁盘 | LUKS（可选） |

```bash
mc encrypt set sse-s3 alias/sensitive-bucket
```

## 网络

- API/Console 仅内网或零信任
- 桶 public 默认禁止
- WAF 防 LIST 扫描

## 审计

`audit_webhook` → SIEM，告警 **匿名策略变更、root 登录**。

## 反模式

- MINIO_ROOT 写进 K8s Secret 给 Pod
- public bucket 存 PII
- HTTP 生产明文

安全基线进 **上线 Checklist**。
