---
title: Argo CD 生产 RBAC 与 SSO 集成
date: 2026-08-27 11:00:00
tags:
  - ArgoCD
  - SRE
  - RBAC
categories:
  - ArgoCD SRE
---

生产环境 **禁用共享 admin**，SSO + 细粒度 RBAC 是底线。

## SSO 架构

```
User → OIDC/SAML (Okta/Azure AD/GitHub)
         → Dex（可选）→ argocd-server
         → argocd-rbac-cm 映射 group → role
```

## OIDC 配置（argocd-cm）

```yaml
oidc.config: |
  name: AzureAD
  issuer: https://login.microsoftonline.com/<tenant>/v2.0
  clientID: xxx
  clientSecret: $oidc.azure.clientSecret
  requestedIDTokenClaims:
    groups:
      essential: true
  requestedScopes:
    - openid
    - profile
    - email
```

## 生产 RBAC 策略

```yaml
# argocd-rbac-cm
policy.default: role:readonly
policy.csv: |
  p, role:org-admin, *, *, */*, allow
  p, role:platform, applications, *, */*, allow
  p, role:developer, applications, get, */*, allow
  p, role:developer, applications, sync, team-a/*, allow
  p, role:sre-prod, applications, sync, production/*, allow
  g, platform-team, role:platform
  g, backend-devs, role:developer
  g, sre-oncall, role:sre-prod
  g, sre-oncall, role:org-admin
scopes: '[groups, email]'
```

## 禁用本地 admin

```yaml
# argocd-cm
admin.enabled: "false"
```

保留 break-glass 紧急账号文档于保险库。

## Project 级角色

```yaml
# AppProject spec.roles
roles:
  - name: prod-sync
    policies:
      - p, proj:production:prod-sync, applications, sync, production/*, allow
    groups:
      - sre-oncall
```

## 审计验证

```bash
argocd account can-i sync applications production/my-app
argocd account list
```

## 反模式

- CI 使用 admin token
- SSO group 映射过宽（全员 org-admin）
- 无 break-glass 流程

RBAC 变更走 PR，**staging 先验证**再推 prod Argo CD。
