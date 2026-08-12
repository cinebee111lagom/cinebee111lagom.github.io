---
title: MinIO 监控与 Prometheus 入门
date: 2026-09-01 12:30:00
tags:
  - MinIO
  - Prometheus
  - 入门
categories:
  - MinIO 新手入门
---

MinIO 暴露 **Prometheus metrics**，可接 Grafana 可视化。

## 启用指标

```bash
# 环境变量
export MINIO_PROMETHEUS_AUTH_TYPE=public
# 或 jwt 认证

# 指标端点
curl http://localhost:9000/minio/v2/metrics/cluster
curl http://localhost:9000/minio/v2/metrics/bucket
```

## Prometheus scrape

```yaml
scrape_configs:
  - job_name: minio
    metrics_path: /minio/v2/metrics/cluster
    scheme: http
    static_configs:
      - targets: ['minio:9000']
```

## 关键指标

| 指标 | 含义 |
|------|------|
| minio_cluster_capacity_raw_total_bytes | 总容量 |
| minio_cluster_capacity_usable_total_bytes | 可用容量 |
| minio_s3_requests_total | API 请求 |
| minio_s3_traffic_received_bytes | 入流量 |
| minio_cluster_health_status | 健康 |

## Grafana

MinIO 官方提供 Dashboard JSON，或社区 **MinIO Dashboard**。

## 日志

```bash
export MINIO_AUDIT_WEBHOOK_ENABLE=on
# 或容器 stdout
docker logs minio -f
```

## 告警起步

```yaml
- alert: MinIOClusterDown
  expr: up{job="minio"} == 0
  for: 5m

- alert: MinIODiskSpaceLow
  expr: minio_cluster_disk_free_inodes / minio_cluster_disk_total_inodes < 0.1
  for: 15m
```

## 反模式

- 无容量告警
- metrics 公网无认证
- 不监控 API 5xx

下一篇：**纠删码**。
