---
title: Argo CD 多环境管理：Dev、Staging、Prod
date: 2026-08-26 10:45:00
tags:
  - ArgoCD
  - 多环境
  - 入门
categories:
  - ArgoCD 新手入门
---

多环境是 GitOps 最常见场景，推荐 **目录结构 + Kustomize overlay**。

## 推荐仓库结构

```
apps/
└── my-service/
    ├── base/
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   └── kustomization.yaml
    └── overlays/
        ├── dev/
        │   ├── kustomization.yaml
        │   └── patch-replicas.yaml
        ├── staging/
        │   └── kustomization.yaml
        └── prod/
            └── kustomization.yaml
```

## base/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

## overlays/dev/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: my-service-dev
images:
  - name: myapp
    newTag: dev-latest
patches:
  - path: patch-replicas.yaml
```

## 三个 Application

```yaml
# 每个环境一个 Application，path 指向不同 overlay
spec:
  source:
    path: apps/my-service/overlays/dev
  destination:
    namespace: my-service-dev
```

```bash
argocd app create my-service-dev --path apps/my-service/overlays/dev ...
argocd app create my-service-staging --path apps/my-service/overlays/staging ...
argocd app create my-service-prod --path apps/my-service/overlays/prod ...
```

## AppProject 隔离

```yaml
# prod 项目只允许 main 分支
spec:
  sourceRepos:
    - https://github.com/myorg/k8s-manifests.git
  destinations:
    - namespace: my-service-prod
      server: https://prod-cluster
  syncWindows:
    - kind: allow
      schedule: "0 9-18 * * 1-5"
      duration: 9h
```

## 镜像晋级流程

```
CI 构建 → push tag dev-xxx
       → 测试通过 → 改 staging overlay tag → PR merge
       → 测试通过 → 改 prod overlay tag → PR + 审批 → Sync
```

## 反模式

- 三套完全独立的 YAML 复制粘贴
- prod 与 dev 共用一个 Application
- 环境间无 Project/syncWindow 保护

下一篇深入 **Kustomize 与 Argo CD 集成**。
