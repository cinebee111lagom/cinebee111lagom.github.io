---
title: MinIO 分布式集群 HA 与负载均衡生产部署
date: 2026-09-02 09:30:00
tags:
  - MinIO
  - SRE
  - HA
categories:
  - MinIO SRE
---

MinIO 节点 **无单点**，但客户端需 **LB + 健康检查** 才能稳定 HA。

## Nginx LB 示例

```nginx
upstream minio_s3 {
    least_conn;
    server node1:9000 max_fails=3 fail_timeout=30s;
    server node2:9000 max_fails=3 fail_timeout=30s;
    server node3:9000 max_fails=3 fail_timeout=30s;
    server node4:9000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl;
    server_name s3.example.com;
    client_max_body_size 0;
    proxy_buffering off;

    location / {
        proxy_pass http://minio_s3;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 健康检查

```bash
curl -f http://node1:9000/minio/health/live
curl -f http://node1:9000/minio/health/ready
```

LB 仅转发 **ready** 节点。

## Console HA

```
console.example.com → LB:9001 → 各节点 Console
或与 API 同域不同 path（视版本）
```

## 节点故障行为

| 事件 | 影响 |
|------|------|
| 单节点 down | EC 保护，LB 摘除 |
| 单盘 down | 后台 heal |
| 多盘/多节点 | 可能只读/不可用 |

## 验收

```bash
# 停单节点 minio service
mc admin info alias
mc cp test.txt alias/bucket/   # 应成功
```

## 反模式

- DNS 轮询无 health check
- `client_max_body_size` 过小截断大上传
- 仅 Console HA 无 API LB

季度 **节点故障演练**。
