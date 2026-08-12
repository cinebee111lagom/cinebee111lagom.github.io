---
title: Redis 在 Kubernetes 上的 SRE 部署
date: 2026-08-13 16:00:00
tags:
  - Redis
  - Kubernetes
categories:
  - Redis SRE
---

K8s 上跑 Redis 需 Operator 管理有状态 workload，避免手工 StatefulSet 踩坑。

## 常见方案

| 方案 | 说明 |
|------|------|
| **Redis Operator**（Spotahome/OpsTree） | 主从 + Sentinel 自动化 |
| **Redis Cluster Operator** | Cluster 模式 |
| 云厂商 Redis 代理 | 托管式，非自建 Pod |

## Redis Failover Operator 示例

```yaml
apiVersion: databases.spotahome.com/v1
kind: RedisFailover
metadata:
  name: redis-prod
spec:
  sentinel:
    replicas: 3
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
  redis:
    replicas: 3
    resources:
      requests:
        cpu: 500m
        memory: 4Gi
    storage:
      persistentVolumeClaim:
        metadata:
          name: redis-data
        spec:
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 20Gi
```

## SRE 关注点

- **StorageClass**：SSD，延迟稳定
- **Pod 反亲和**：主从分散节点/AZ
- **Resource limits**：与 maxmemory 对齐
- **Headless Service**：Sentinel 发现

## 与外部 Redis 对比

| | K8s 自建 | 外部托管 |
|---|----------|----------|
| 运维 | SRE 全责 | 云厂商 |
| 弹性 | HPA 受限（有状态） | 控制台扩缩 |
| 网络 | Cluster 内低延迟 | 可能跨 VPC |

## 备份

- 定时 Job 执行 `BGSAVE` + 卷快照
- Velero 备份 PVC

K8s 部署 Redis 的核心是 **Operator + 持久卷 + 反亲和**，勿裸 Deployment 单副本上线。
