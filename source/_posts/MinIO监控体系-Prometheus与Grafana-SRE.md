---
title: MinIO 监控体系：Prometheus 与 Grafana
date: 2026-09-02 10:00:00
tags:
  - MinIO
  - SRE
  - Prometheus
categories:
  - MinIO SRE
---

MinIO SRE 依赖 **cluster/bucket/node 三级 metrics**。

## Scrape 配置

```yaml
scrape_configs:
  - job_name: minio-cluster
    metrics_path: /minio/v2/metrics/cluster
    static_configs:
      - targets: ['minio-lb:9000']

  - job_name: minio-bucket
    metrics_path: /minio/v2/metrics/bucket
    static_configs:
      - targets: ['minio-lb:9000']

  - job_name: minio-node
    metrics_path: /minio/v2/metrics/node
    static_configs:
      - targets: ['node1:9000', 'node2:9000', 'node3:9000', 'node4:9000']
```

## 关键 SLI

| 指标 | SLI |
|------|-----|
| minio_cluster_health_status | 健康 |
| minio_cluster_capacity_usable_free_bytes | 容量 |
| minio_s3_requests_4xx/5xx | 错误率 |
| minio_s3_requests_duration_seconds | 延迟 |
| minio_heal_objects_heal_total | 自愈 |

## Grafana Dashboard

- MinIO 官方 Grafana 模板
- 面板：容量趋势、Top bucket、API QPS、节点 disk

## 日志与审计

```bash
mc admin config set alias audit_webhook:1 \
  enable=on endpoint=https://siem/logs/auth_token=xxx
```

## 反模式

- 只监控 cluster 不监控 node
- 无 bucket 级容量 Top N
- metrics 公网暴露

**容量可用 < 15% → P1**。
