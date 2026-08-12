---
title: Argo CD 生产安全配置与网络隔离
date: 2026-08-27 11:45:00
tags:
  - ArgoCD
  - SRE
  - 安全
categories:
  - ArgoCD SRE
---

Argo CD 持有 **多集群部署权限**，是攻击者高价值目标。

## 网络隔离

| 层 | 措施 |
|----|------|
| Ingress | 仅内网/VPN，WAF 可选 |
| NetworkPolicy | argocd namespace 限制入站 |
| Egress | repo-server 仅允许 Git/Helm registry |
| API | 禁止 argocd-server 公网无 SSO |

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-server-ingress
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-server
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - port: 8080
```

## 高危功能

| 功能 | 生产建议 |
|------|----------|
| Web Terminal (exec) | 禁用 |
| admin 本地账号 | 禁用 |
| anonymous 访问 | 禁用 |
| `--enable-gzip` 等 | 按需 |

```yaml
# argocd-cm
exec.enabled: "false"
admin.enabled: "false"
```

## 供应链安全

- Git 仓库 branch protection + signed commit
- Container 镜像 pin digest
- Helm chart 来自可信 repo，pin version
- SBOM 扫描 Argo CD 镜像

## Secret 管理

- repo credential 用 K8s Secret + RBAC 限制
- 优先 GitHub App 而非 PAT
- cluster token 最小权限 + 轮换

## 审计与合规

```yaml
audit.log.format: json
audit.log.maxage: "365"
```

接入 SIEM，告警 **非授权 sync prod**。

## 反模式

- argocd-server LoadBalancer 公网暴露
- cluster secret 使用 cluster-admin
- 无 NetworkPolicy 的 argocd namespace

安全配置纳入 **上线 Checklist**（本系列第 19 篇）。
