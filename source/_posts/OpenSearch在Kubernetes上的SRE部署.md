---
title: OpenSearch 在 Kubernetes 上的 SRE 部署
date: 2026-08-20 11:45:00
tags:
  - OpenSearch
  - Kubernetes
categories:
  - OpenSearch SRE
---

K8s 上部署 OpenSearch 常用 **OpenSearch Operator** 或 Helm Chart。

## OpenSearch Operator 示例

```yaml
apiVersion: opensearch.opster.io/v1
kind: OpenSearchCluster
metadata:
  name: prod-cluster
spec:
  general:
    version: 2.14.0
    httpPort: 9200
    serviceName: prod-cluster
    pluginsList: ["repository-s3"]
  nodePools:
    - component: masters
      replicas: 3
      diskSize: "50Gi"
      roles:
        - cluster_manager
      resources:
        requests:
          memory: "4Gi"
          cpu: "1"
    - component: data
      replicas: 3
      diskSize: "500Gi"
      roles:
        - data
        - ingest
      resources:
        requests:
          memory: "16Gi"
          cpu: "4"
  confMgmt:
    smartScaler: true
  dashboards:
    enable: true
    version: 2.14.0
    replicas: 1
```

## 存储

```yaml
storageClass: gp3
volumeMode: Filesystem
# 每 data 节点独立 PVC，禁止 EmptyDir
```

## 快照到 S3

```yaml
# 配置 keystore + repository-s3 插件
# ServiceAccount IRSA 访问 S3
```

## 滚动升级

```yaml
spec:
  general:
    version: 2.15.0  # 改版本触发滚动
```

Operator 按 nodePool 顺序滚动，确保 quorum。

## 监控

- PodMonitor 抓取 9200 metrics
- 日志 stdout → Loki

## SRE 注意

| 项 | 建议 |
|----|------|
| PDB | cluster_manager minAvailable 2 |
| 反亲和 | spread 跨 AZ |
| 内存 | requests=limits 避免 OOM 漂移 |
| sysctl | initContainer 设 vm.max_map_count |

## 检查清单

- [ ] 3 cluster_manager + 3 data
- [ ] PVC 存储类 IOPS 满足写入
- [ ] Security 证书 Secret 管理
- [ ] Snapshot 仓库配置
- [ ] 升级 staging 验证

K8s 部署与 **Filebeat DaemonSet** 同集群时注意网络与 RBAC。
