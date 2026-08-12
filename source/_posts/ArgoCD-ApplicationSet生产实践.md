---
title: Argo CD ApplicationSet 生产实践
date: 2026-08-27 10:45:00
tags:
  - ArgoCD
  - SRE
  - ApplicationSet
categories:
  - ArgoCD SRE
---

ApplicationSet 解决 **百应用批量创建** 问题，平台团队 SRE 必备。

## 典型场景

| Generator | 用途 |
|-----------|------|
| Git | monorepo 目录扫描 |
| Cluster | 多集群相同应用 |
| List | 固定应用列表 |
| Matrix | Git × Cluster 组合 |
| SCM Provider | 自动发现 GitHub org repos |

## Git Generator 示例

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: team-apps
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/myorg/k8s-manifests.git
        revision: main
        directories:
          - path: apps/*
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: team-a
      source:
        repoURL: https://github.com/myorg/k8s-manifests.git
        targetRevision: main
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
      syncPolicy:
        syncOptions:
          - CreateNamespace=true
```

## 多集群 Matrix

```yaml
generators:
  - matrix:
      generators:
        - git:
            repoURL: ...
            directories:
              - path: apps/*
        - clusters:
            selector:
              matchLabels:
                env: prod
```

为每个 app × 每个 prod 集群生成 Application。

## 生产治理

| 项 | 建议 |
|----|------|
| Project 限制 | ApplicationSet 只能创建指定 Project 内 app |
| syncPolicy | prod 模板默认 manual sync |
| 命名 | `{{name}}-{{cluster}}` 防冲突 |
| 预览 | `argocd appset generate` |

## 故障排查

```bash
kubectl get applicationset -n argocd
kubectl describe applicationset team-apps -n argocd
kubectl logs -n argocd deploy/argocd-applicationset-controller
```

## 反模式

- Generator 路径过宽 `apps/**` 误纳无关目录
- 无 Project 边界，自动创建 prod Application
- 与手工 Application 重名冲突

ApplicationSet manifest 应 **Git 管理**，纳入 code review。
