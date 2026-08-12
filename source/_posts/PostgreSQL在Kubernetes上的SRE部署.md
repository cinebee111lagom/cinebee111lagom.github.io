---
title: PostgreSQL 在 Kubernetes 上的 SRE 部署
date: 2026-08-15 12:00:00
tags:
  - PostgreSQL
  - Kubernetes
  - SRE
categories:
  - PostgreSQL SRE
---

K8s 上运行 PostgreSQL 常用 Operator 管理 HA、备份与扩缩容。

## 主流 Operator

| Operator | 特点 |
|----------|------|
| Crunchy PGO | 成熟、pgBackRest 集成 |
| Zalando Postgres Operator | Patroni、逻辑备份 |
| CloudNativePG | CNCF，原生 K8s 设计 |

## CloudNativePG 示例

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: pg-cluster
spec:
  instances: 3
  storage:
    size: 100Gi
    storageClass: fast-ssd
  postgresql:
    parameters:
      shared_buffers: "1GB"
      max_connections: "200"
  backup:
    barmanObjectStore:
      destinationPath: s3://mybucket/pg-backup
      s3Credentials:
        accessKeyId:
          name: backup-creds
          key: ACCESS_KEY
        secretAccessKey:
          name: backup-creds
          key: SECRET_KEY
  monitoring:
    enablePodMonitor: true
```

## 存储要点

- 使用 **ReadWriteOnce** SSD StorageClass
- WAL 与数据可同卷，大负载可分离
- 禁止 EmptyDir 存生产数据

## 网络

```yaml
# Service：写走 primary，读可走 replica service
apiVersion: v1
kind: Service
metadata:
  name: pg-rw
  annotations:
    cnpg.io/role: primary
```

应用通过 PgBouncer Sidecar 或集群外 PgBouncer 连接。

## 备份与 PITR

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
metadata:
  name: pg-daily
spec:
  schedule: "0 2 * * *"
  cluster:
    name: pg-cluster
  backupOwnerReference: self
```

## SRE 注意

| 项 | 建议 |
|----|------|
| 资源 limit | CPU/memory 与 shared_buffers 匹配 |
| PDB | 至少保留 1 副本可调度 |
| 节点亲和 | 反亲和 spread 跨 AZ |
| 升级 | Operator 滚动升级 + 先 staging |
| 调试 | `kubectl cnpg psql` / exec 进 pod |

## 检查清单

- [ ] 3 副本 + 跨 AZ
- [ ] 备份到对象存储 + 演练
- [ ] PodMonitor + 告警
- [ ] 存储类 IOPS 满足 WAL 写入
- [ ] 不在 K8s 跑无 Operator 的单点 PG

K8s 适合弹性与 GitOps，**数据持久化与备份**仍是 SRE 核心责任。
