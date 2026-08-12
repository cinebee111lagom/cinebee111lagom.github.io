---
title: MinIO 与应用程序 SDK 集成入门
date: 2026-09-01 12:15:00
tags:
  - MinIO
  - SDK
  - 入门
categories:
  - MinIO 新手入门
---

MinIO 兼容 S3 SDK，换 **endpoint** 即可从 AWS 迁移到私有 MinIO。

## Python boto3

```python
import boto3
s3 = boto3.client('s3',
    endpoint_url='http://minio:9000',
    aws_access_key_id='appuser',
    aws_secret_access_key='secret',
    region_name='us-east-1',
)
s3.create_bucket(Bucket='mybucket')
s3.put_object(Bucket='mybucket', Key='hello.txt', Body=b'hello')
```

## Go minio-go

```go
import "github.com/minio/minio-go/v7"
import "github.com/minio/minio-go/v7/pkg/credentials"

client, _ := minio.New("minio:9000", &minio.Options{
    Creds:  credentials.NewStaticV4("appuser", "secret", ""),
    Secure: false,
})
client.FPutObject(ctx, "mybucket", "obj.bin", "/path/local.bin", minio.PutObjectOptions{})
```

## Java AWS SDK v2

```java
S3Client s3 = S3Client.builder()
    .endpointOverride(URI.create("http://minio:9000"))
    .credentialsProvider(StaticCredentialsProvider.create(
        AwsBasicCredentials.create("appuser", "secret")))
    .region(Region.US_EAST_1)
    .forcePathStyle(true)
    .build();
```

## 关键参数

| 参数 | 说明 |
|------|------|
| endpoint_url | MinIO 地址 |
| forcePathStyle | 通常 true（MinIO） |
| region | 任意一致即可 |
| signature v4 | 必须 |

## 框架集成

| 框架 | 配置 |
|------|------|
| Spring | `spring.cloud.aws.s3.endpoint` |
| Laravel | `AWS_ENDPOINT` |
| GitLab | `object_store` 兼容 S3 |

## 反模式

- 硬编码密钥
- 未设 path style 导致 403
- 混用 v2 签名（旧）

下一篇：**监控**。
