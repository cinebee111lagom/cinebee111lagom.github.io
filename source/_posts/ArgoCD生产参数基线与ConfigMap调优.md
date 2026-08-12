---
title: Argo CD 生产参数基线与 ConfigMap 调优
date: 2026-08-27 09:45:00
tags:
  - ArgoCD
  - SRE
  - 基线
categories:
  - ArgoCD SRE
---

`argocd-cm`、`argocd-cmd-params-cm`、`argocd-rbac-cm` 是生产调优核心。

## argocd-cm 关键项

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  timeout.reconciliation: 180s
  application.resourceTrackingMethod: annotation
  resource.customizations.ignoreResourceUpdates.all: |
    jsonPointers:
      - /status
  url: https://argocd.example.com
  oidc.config: |
    name: OIDC
    issuer: https://sso.example.com
    clientID: argocd
    clientSecret: $oidc.argocd.clientSecret
    requestedScopes: ["openid", "profile", "email", "groups"]
```

## cmd-params 性能相关

```yaml
# argocd-cmd-params-cm
data:
  reposerver.parallelism.limit: "10"
  controller.status.processors: "20"
  controller.operation.processors: "10"
  controller.self.heal.timeout.seconds: "5"
  server.insecure: "false"
```

## 生产基线 Checklist

| 项 | 推荐值 |
|----|--------|
| reconciliation 周期 | 180s（大集群可 300s） |
| resourceTrackingMethod | annotation（减少 label 冲突） |
| application.instanceLabelKey | 保持默认或团队统一 |
| exec.enabled | false（生产禁用 Web Terminal） |
| admin.enabled | false（SSO 后禁用本地 admin） |

## 超时与 Git 大仓

```yaml
data:
  reposerver.git.requestTimeout: 120s
  reposerver.git.lsremoteParallelismLimit: "5"
```

Monorepo 过大时应 **拆分 repo** 而非无限调超时。

## 审计

```yaml
data:
  audit.log.format: json
  audit.log.maxage: "90"
```

## 变更流程

1. staging 集群改 ConfigMap
2. 观察 controller/repo-server 日志与 Sync 延迟
3. 滚动 restart：`kubectl rollout restart -n argocd`

## 反模式

- 生产 `exec.enabled: true` 无 RBAC 限制
- reconciliation 过短导致 controller CPU 飙高
- ConfigMap 变更无 Git 记录（应 Helm/GitOps 管理 Argo CD 自身）

Argo CD **自举（self-manage）**：用 Application 管理 argocd namespace 配置。
