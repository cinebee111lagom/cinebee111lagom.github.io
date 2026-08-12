---
title: MinIO TLS 与 HTTPS 配置入门
date: 2026-09-01 11:45:00
tags:
  - MinIO
  - TLS
  - 入门
categories:
  - MinIO 新手入门
---

生产 **必须 HTTPS**，保护传输中的 Access Key 与数据。

## 证书放置

MinIO 自动加载：

```
~/.minio/certs/
  public.crt
  private.key
  CAs/          # 可选，客户端 CA
```

或指定目录：

```bash
export MINIO_CERTS_DIR=/etc/minio/certs
minio server /data/minio --console-address ":9001"
```

## 自签名（测试）

```bash
openssl req -newkey rsa:4096 -nodes -keyout private.key -x509 -days 365 -out public.crt \
  -subj "/CN=minio.example.com"
mkdir -p /etc/minio/certs
cp public.crt private.key /etc/minio/certs/
```

## Let's Encrypt（生产）

通过 **Certbot + Nginx** 在 LB 终止 TLS，MinIO 内网 HTTP；或 **minio 直接挂证书**。

## mc 连接 HTTPS

```bash
mc alias set secure https://minio.example.com:9000 admin 'pass'
# 自签名需 --insecure 或导入 CA
mc alias set secure https://minio.example.com:9000 admin 'pass' --api S3v4
```

## SDK endpoint

```python
endpoint_url='https://minio.example.com:9000'
# verify='/path/to/ca.crt'  # 自签名 CA
```

## 反模式

- 生产 HTTP 明文
- 证书过期无监控
- Console 9001 无 TLS 暴露公网

下一篇：**K8s 部署**。
