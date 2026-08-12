---
title: MySQL 在 Kubernetes 上的 SRE 部署
date: 2026-08-14 12:00:00
tags:
  - MySQL
  - Kubernetes
categories:
  - MySQL SRE
---

K8s 有状态 MySQL 需 Operator 管理，避免裸 StatefulSet 运维噩梦。

## 常见 Operator

| Operator | 特点 |
|----------|------|
| **Percona Operator** | PXB 备份、HA Proxy |
| **Oracle MySQL Operator** | 官方 InnoDB Cluster |
| **Vitess** | 分片 + K8s 原生 |
| **Presslabs** | 主从 + 备份 |

## Percona 示例片段

```yaml
apiVersion: pxc.percona.com/v1
kind: PerconaXCluster
metadata:
  name: mysql-prod
spec:
  pxc:
    size: 3
    resources:
      requests:
        memory: 8Gi
        cpu: 2
    volumeSpec:
      persistentVolumeClaim:
        resources:
          requests:
            storage: 200Gi
  backup:
    schedule:
      - name: daily
        schedule: "0 2 * * *"
        keep: 7
```

## SRE 关注点

- **StorageClass**：SSD，IOPS 保障
- **Pod 反亲和**：跨节点/AZ
- **资源 limits**：与 innodb_buffer_pool 匹配
- **备份 Job**：对象存储 + 恢复演练

## 与外部 RDS

| | K8s 自建 | RDS |
|---|----------|-----|
| 备份 | 自管 PXB | 自动快照 |
| 升级 | Operator 滚动 | 控制台 |
| 故障 | SRE 全责 | SLA 分担 |

K8s MySQL 核心：**Operator + PVC + 备份自动化**。
