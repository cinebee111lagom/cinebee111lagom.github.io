---
title: MinIO 与 Kubernetes 部署入门
date: 2026-09-01 12:00:00
tags:
  - MinIO
  - Kubernetes
  - 入门
categories:
  - MinIO 新手入门
---

K8s 上常用 **MinIO Operator** 部署 **Tenant**（独立 MinIO 实例）。

## 安装 Operator

```bash
kubectl apply -k "github.com/minio/operator?ref=v5.0.0"
kubectl get pods -n minio-operator
```

## 创建 Tenant（简化示例）

```yaml
apiVersion: minio.min.io/v2
kind: Tenant
metadata:
  name: minio-tenant
  namespace: minio
spec:
  credsSecret:
    name: minio-creds
  pools:
    - servers: 4
      volumesPerServer: 4
      volumeClaimTemplate:
        spec:
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 100Gi
  requestAutoCert: false
  certConfig:
    commonName: minio.minio.svc
```

```bash
kubectl apply -f tenant.yaml
kubectl get pods -n minio
```

## 访问

```bash
kubectl port-forward svc/minio-tenant-hl 9000:9000 -n minio
mc alias set k8sminio http://localhost:9000 minio minio123
```

生产用 **Ingress** 暴露 API/Console。

## 与 Velero 备份

```yaml
# Velero 使用 MinIO 作 backup storage
configuration:
  backupStorageLocation:
    - name: default
      bucket: velero
      config:
        region: minio
        s3ForcePathStyle: "true"
        s3Url: http://minio.minio.svc:9000
```

## Helm 替代

```bash
helm repo add minio https://charts.min.io/
helm install minio minio/minio --set mode=distributed,replicas=4
```

## 反模式

- Tenant 无持久化 PVC
- 单副本「分布式」
- root 密码硬编码在 YAML 进 Git

下一篇：**SDK 集成**。
