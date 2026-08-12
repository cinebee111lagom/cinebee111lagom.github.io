---
title: Argo CD HA 生产部署与 Redis 高可用
date: 2026-08-27 09:30:00
tags:
  - ArgoCD
  - SRE
  - HA
categories:
  - ArgoCD SRE
---

生产 Argo CD 必须 **HA**，Redis 是常见单点，需重点设计。

## HA 组件清单

| 组件 | 生产配置 |
|------|----------|
| argocd-server | replicas ≥ 2，PDB minAvailable 1 |
| argocd-repo-server | replicas ≥ 2 |
| argocd-application-controller | sharding（大规模） |
| redis | Redis HA（Helm subchart） |
| Dex | 随 server 或无状态 OIDC |

## Helm 生产 values 片段

```yaml
redis-ha:
  enabled: true
  haproxy:
    enabled: true

server:
  replicas: 2
  ingress:
    enabled: true
    hosts:
      - argocd.example.com
  resources:
    requests:
      cpu: 250m
      memory: 512Mi

repoServer:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 1Gi

controller:
  replicas: 1
  # 大规模启用 sharding：
  # env: ARGOCD_CONTROLLER_REPLICAS=3

global:
  domain: argocd.example.com
```

## 验收

```bash
kubectl get pods -n argocd
kubectl get pdb -n argocd
argocd version
argocd cluster list

# 模拟 server pod 删除，UI 仍可用
kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-server --force
```

## Redis 故障影响

| 影响 | 说明 |
|------|------|
| 缓存失效 | 短暂性能下降，可自愈 |
| 完全不可用 | Sync 状态延迟，需快速恢复 |

**Git 仍是真相来源**，Redis 故障不丢部署定义，但应 P1 告警。

## 反亲和与节点分布

```yaml
server:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-server
          topologyKey: kubernetes.io/hostname
```

## 反模式

- 单副本 controller 无 PDB
- Redis 无持久化且无恢复演练
- Ingress 未配 health check 导致流量打到 Terminating pod

HA 部署后做 **控制面故障切换演练**（见本系列故障演练篇）。
