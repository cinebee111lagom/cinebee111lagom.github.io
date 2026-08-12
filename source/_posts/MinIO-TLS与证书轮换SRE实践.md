---
title: MinIO TLS 与证书轮换 SRE 实践
date: 2026-09-02 12:00:00
tags:
  - MinIO
  - SRE
  - TLS
categories:
  - MinIO SRE
---

证书过期会导致 **全站 S3 不可用**，需自动化轮换与告警。

## 部署模式

| 模式 | 轮换点 |
|------|--------|
| LB 终止 TLS | Certbot/LB 证书 |
| MinIO 直连 TLS | MINIO_CERTS_DIR |
| K8s cert-manager | Tenant certConfig |

## MinIO 证书目录

```
/etc/minio/certs/
  public.crt
  private.key
  CAs/ca.crt   # 私有 CA 链
```

轮换后：

```bash
systemctl reload minio
# 或 mc admin service restart alias --rolling
curl -v https://s3.example.com/minio/health/live
```

## 监控

```yaml
- alert: MinIOTLSCertExpiring
  expr: probe_ssl_earliest_cert_expiry{job="blackbox-s3"} - time() < 86400 * 14
  for: 1h
```

blackbox_exporter HTTPS probe。

## 客户端 CA 更新

SDK 需信任新 CA，**双证书过渡期**（旧+新并存 7 天）。

## 反模式

- 自签名无监控
- 只 renew LB 忘记 MinIO 直连路径
- 轮换无 staging 验证

证书轮换 **Runbook 每季度演练**。
