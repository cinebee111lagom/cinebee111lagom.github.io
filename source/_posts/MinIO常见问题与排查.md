---
title: MinIO 常见问题与排查
date: 2026-09-01 13:30:00
tags:
  - MinIO
  - 排查
  - 入门
categories:
  - MinIO 新手入门
---

MinIO 值班常见问题与 **第一步排查**。

## 无法连接

| 现象 | 排查 |
|------|------|
| Connection refused | 进程/端口 9000 |
| SSL error | 证书/CA |
| 403 | 密钥/Policy/时钟 |

```bash
curl http://localhost:9000/minio/health/live
mc admin info local
```

## Access Denied

```bash
mc admin policy info local my-policy
mc admin user info local appuser
# 检查 Resource ARN、bucket 名
```

## 磁盘/空间

```bash
mc admin info local
df -h /data/minio
# 满盘 → 扩容或 lifecycle 清理
```

## 分布式节点不一致

```bash
mc admin heal local
mc admin heal local --recursive mybucket
```

## 上传慢

- 检查网络带宽
- multipart 阈值
- 磁盘 IO（iostat）
- 反代 body size 限制（Nginx `client_max_body_size`）

## 复制 lag

```bash
mc replicate backlog local/mybucket
mc admin replicate resync local mybucket
```

## 日志

```bash
journalctl -u minio -f
export MINIO_LOG_LEVEL=debug  # 临时
```

## 排查流程

```
连不上 → health → 网络/证书
403 → user/policy
慢 → 磁盘/网络/metrics
丢对象 → versioning/heal/replication
```

收藏作 **MinIO 速查**。
