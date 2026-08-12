---
title: MinIO 与 Kubernetes Operator 生产运维
date: 2026-09-02 12:15:00
tags:
  - MinIO
  - SRE
  - Kubernetes
categories:
  - MinIO SRE
---

K8s 上 **MinIO Operator + Tenant** 是云原生常见部署，SRE 需懂 CR 生命周期。

## 架构

```
minio-operator namespace → Operator
minio namespace → Tenant CR → StatefulSet Pool
Ingress → S3 API / Console
```

## 生产 Tenant 要点

| 项 | 建议 |
|----|------|
| pools.servers | ≥ 4 |
| volumesPerServer | ≥ 4 |
| storageClass | 本地 SSD / 高性能 CSI |
| requestAutoCert | false，用 cert-manager |
| env | 资源 limit、审计 webhook |

## 运维命令

```bash
kubectl minio tenant list -n minio
kubectl minio tenant info minio-tenant -n minio
kubectl get pods -n minio -w
```

## 扩容 Pool

```yaml
spec:
  pools:
    - servers: 4
      volumesPerServer: 4
      # 增加 pool-1 或扩 PVC（视版本能力）
```

遵循 Operator 文档 **扩 pool 而非单 Pod 扩盘乱序**。

## 监控

- Pod metrics + MinIO cluster metrics
- PVC 使用率告警

## 反模式

- 单 Pod Tenant 生产
- 与业务 Pod 混节点无 taint
- root Secret 进 Git

Operator 升级与 **Tenant 升级分开** 测试。
