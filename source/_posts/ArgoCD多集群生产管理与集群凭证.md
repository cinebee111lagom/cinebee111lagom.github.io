---
title: Argo CD 多集群生产管理与集群凭证
date: 2026-08-27 10:30:00
tags:
  - ArgoCD
  - SRE
  - 多集群
categories:
  - ArgoCD SRE
---

Hub-Spoke 模式下，**集群注册与凭证轮换**是 SRE 核心日常。

## 注册集群

```bash
# CLI 方式（生成 cluster secret）
argocd cluster add prod-context --name production \
  --system-namespace argocd \
  --label env=prod

argocd cluster list
argocd cluster get production
```

## 集群 Secret 结构

Argo CD 在 `argocd` namespace 创建 `cluster-<hash>` Secret，含：

- `server`：API Server URL
- `config`：Bearer token 或 TLS 客户端证书
- `namespaces`：允许部署的 namespace 列表（可选）

## 凭证最佳实践

| 实践 | 说明 |
|------|------|
| 专用 SA | 每集群 `argocd-manager` ServiceAccount |
| 最小 RBAC | 仅所需 namespace ClusterRoleBinding |
| 定期轮换 | 90 天轮换 token |
| 标签 | env、region、cost-center |

```yaml
# 远程集群 RBAC 示例（简化）
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argocd-manager
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: argocd-manager-role
subjects:
  - kind: ServiceAccount
    name: argocd-manager
    namespace: argocd
```

## 网络要求

```
Mgmt 集群 argocd-application-controller
    → TCP 443 → Spoke API Server
```

EKS/GKE 需 **PrivateLink / 内网 LB / 堡垒机代理**。

## 故障排查

```bash
argocd cluster get production
# Connection State: Failed → 查网络/证书/token

kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller | grep production
```

## 反模式

- 使用 cluster-admin token
- 凭证永不过期
- 生产与测试集群共用 Spoke 凭证

集群清单纳入 CMDB：**名称、API、注册时间、上次轮换**。
