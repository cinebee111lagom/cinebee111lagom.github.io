---
title: Argo CD 核心概念：Application、Project、Repo
date: 2026-08-26 09:45:00
tags:
  - ArgoCD
  - 入门
categories:
  - ArgoCD 新手入门
---

Argo CD 的三个核心 CRD 构成 GitOps 管理模型。

## Application

**一个 Application = 一个 Git 源 + 一个 K8s 目标**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

| 字段 | 含义 |
|------|------|
| source.repoURL | Git 仓库地址 |
| source.path | 仓库内 Manifest 路径 |
| source.targetRevision | 分支/tag/commit |
| destination.server | 目标集群 API |
| destination.namespace | 部署命名空间 |

## Project

**Project = 多租户边界**，限制哪些仓库、哪些集群、哪些资源类型。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-a
  namespace: argocd
spec:
  sourceRepos:
    - https://github.com/myorg/team-a-*
  destinations:
    - namespace: team-a-*
      server: https://kubernetes.default.svc
  clusterResourceWhitelist:
    - group: ""
      kind: Namespace
```

默认有 `default` Project，生产应拆分。

## Repository

Argo CD 需 **注册 Git 仓库凭证**（公开仓可免密）。

```bash
# CLI 添加
argocd repo add https://github.com/myorg/k8s-manifests.git \
  --username git --password <token>

# 查看
argocd repo list
```

私有仓常用 **Deploy Key** 或 **Personal Access Token**。

## 关系图

```
AppProject（边界）
    └── Application（应用）
            ├── source → Repository（Git）
            └── destination → Cluster + Namespace
```

## Application of Applications（App of Apps）

用父 Application 管理多个子 Application，适合 **平台/bootstrap** 场景。

```
bootstrap-app（Git 根目录）
  ├── infra-app
  ├── monitoring-app
  └── team-a-app
```

## 反模式

- 所有应用放 default Project 无隔离
- Application 指向过宽的 Git 根目录
- 私有仓 token 过期未监控

下一篇：**argocd CLI** 与第一个 Nginx 实战。
