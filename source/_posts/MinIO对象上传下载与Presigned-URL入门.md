---
title: MinIO 对象上传下载与 Presigned URL 入门
date: 2026-09-01 10:45:00
tags:
  - MinIO
  - 上传
  - 入门
categories:
  - MinIO 新手入门
---

大文件上传、浏览器直传常用 **Presigned URL**，无需暴露 Secret Key。

## mc 上传下载

```bash
# 单文件
mc cp report.pdf local/mybucket/docs/report.pdf

# 大文件（自动 multipart）
mc cp large.iso local/mybucket/images/

# 下载
mc cp local/mybucket/docs/report.pdf ./

# 显示进度
mc cp --json large.bin local/mybucket/
```

## aws cli 兼容

```bash
aws configure set aws_access_key_id appuser
aws configure set aws_secret_access_key AppSecret123!

aws --endpoint-url http://localhost:9000 s3 cp file.txt s3://mybucket/
aws --endpoint-url http://localhost:9000 s3 ls s3://mybucket/
```

## Presigned URL（mc）

```bash
# 下载链接，7 天有效
mc share download --expire 168h local/mybucket/private/doc.pdf

# 上传链接（PUT）
mc share upload --expire 1h local/mybucket/incoming/
```

## Python boto3 示例

```python
import boto3
from botocore.client import Config

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='appuser',
    aws_secret_access_key='AppSecret123!',
    config=Config(signature_version='s3v4'),
)

s3.upload_file('local.txt', 'mybucket', 'remote.txt')
s3.download_file('mybucket', 'remote.txt', 'downloaded.txt')
```

## Multipart 大文件

超过 5MB 建议 multipart（SDK/mc 自动处理）。

## 反模式

- 把 Secret Key 放前端 JS
- presigned URL 过期时间过长
- 不经 TLS 传敏感文件（生产）

下一篇：**版本控制**。
