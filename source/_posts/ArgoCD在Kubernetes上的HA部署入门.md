---
title: Argo CD 在 Kubernetes 上的 HA 部署入门
date: 2026-08-26 13:15:00
tags:
  - ArgoCD
  - HA
  - 入门
categories:
  - ArgoCD 新手入门
---

生产环境 Argo CD 控制面需 **高可用**，避免单点影响全部交付。

## HA 架构组件

| 组件 | HA 方式 |
|------|---------|
| argocd-server | Deployment replicas ≥ 2 |
| argocd-repo-server | replicas ≥ 2 |
| argocd-application-controller | shards 或多副本（版本相关） |
| Redis | Redis HA（Sentinel/云托管） |
| Dex | 随 server 或无状态 |

官方 `install.yaml` 默认为单副本，生产用 **Helm values** 开启 HA。

## Helm HA 示例

```yaml
# values-ha.yaml
redis-ha:
  enabled: true

controller:
  replicas: 1   # 2.5+ 支持 sharding

server:
  replicas: 2
  autoscaling:
    enabled: true
    minReplicas: 2

repoServer:
  replicas: 2
```

```bash
helm upgrade argocd argo/argo-cd -n argocd -f values-ha.yaml
```

## Ingress 与 TLS

```yaml
server:
  ingress:
    enabled: true
    hosts:
      - argocd.example.com
    tls:
      - secretName: argocd-tls
        hosts:
          - argocd.example.com
  extraArgs:
    - --insecure   # 若 Ingress 终止 TLS
```

## 多集群管理

```bash
# 注册远程集群
argocd cluster add prod-context --name production
argocd cluster add staging-context --name staging
```

Argo CD 在管理集群运行，通过 **cluster secret** 连接远程 API。

## 备份

关键数据：

| 数据 | 备份方式 |
|------|----------|
| Git 仓库 | Git 本身即备份 |
| argocd-secret | Velero / etcd backup |
| Redis | Redis 持久化或可重建 |
| Application CR | Git（App of Apps） |

## 资源建议（中等规模）

| 组件 | CPU | Memory |
|------|-----|--------|
| server ×2 | 250m | 512Mi |
| repo-server ×2 | 500m | 1Gi |
| controller | 1 | 2Gi |

## 反模式

- 生产单副本 controller
- Redis 无持久化且无 Git 恢复路径
- Ingress 无 TLS

HA 是 **ArgoCD SRE 系列** 深入话题，入门先理解组件角色即可。
