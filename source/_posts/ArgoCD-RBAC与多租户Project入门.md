---
title: Argo CD RBAC 与多租户 Project 入门
date: 2026-08-26 12:30:00
tags:
  - ArgoCD
  - RBAC
  - 入门
categories:
  - ArgoCD 新手入门
---

多团队共用 Argo CD 时，**AppProject + RBAC** 实现隔离。

## AppProject 限制维度

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-backend
  namespace: argocd
spec:
  description: Backend team apps
  sourceRepos:
    - https://github.com/myorg/k8s-manifests.git
  destinations:
    - namespace: backend-*
      server: https://kubernetes.default.svc
  namespaceResourceWhitelist:
    - group: apps
      kind: Deployment
    - group: ""
      kind: Service
  roles:
    - name: developer
      policies:
        - p, proj:team-backend:developer, applications, get, team-backend/*, allow
        - p, proj:team-backend:developer, applications, sync, team-backend/*, allow
      groups:
        - backend-devs
```

## 内置 RBAC 模型

Casbin 策略格式：

```
p, <role>, <resource>, <action>, <object>, <effect>
g, <user/group>, <role>
```

| resource | action 示例 |
|----------|-------------|
| applications | get, create, update, delete, sync, override |
| repositories | get, create |
| clusters | get |
| projects | get |

## 配置位置

```yaml
# argocd-rbac-cm ConfigMap
data:
  policy.default: role:readonly
  policy.csv: |
    p, role:org-admin, applications, *, */*, allow
    p, role:developer, applications, get, */*, allow
    p, role:developer, applications, sync, team-a/*, allow
    g, developer@myorg.com, role:developer
```

## SSO 集成（Dex）

```yaml
# argocd-cm
dex.config: |
  connectors:
    - type: github
      id: github
      name: GitHub
      config:
        clientID: xxx
        clientSecret: xxx
        orgs:
          - name: myorg
```

登录后 GitHub team 映射到 RBAC group。

## 多租户最佳实践

| 实践 | 说明 |
|------|------|
| 每团队一个 Project | 限制 namespace 前缀 |
| prod Sync 仅 SRE | developer 只读 prod |
| 独立 repo 路径 | apps/team-a/* |
| audit log | 记录谁 sync 了 prod |

## CLI 验证

```bash
argocd proj list
argocd proj get team-backend
argocd account can-i sync applications team-backend/my-app
```

## 反模式

- 全员 admin
- default Project 无限制
- prod 无 sync 权限分离

下一篇：**Argo CD UI** 使用入门。
