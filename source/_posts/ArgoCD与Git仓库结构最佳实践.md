---
title: Argo CD 与 Git 仓库结构最佳实践
date: 2026-08-26 11:30:00
tags:
  - ArgoCD
  - Git
  - 入门
categories:
  - ArgoCD 新手入门
---

好的仓库结构决定 GitOps 能否 scale 到百应用、多团队。

## Monorepo vs Multirepo

| 模式 | 优点 | 缺点 |
|------|------|------|
| Monorepo | 统一 PR、依赖可见 | 权限粗、repo 大 |
| Multirepo | 团队自治 | 跨应用协调难 |
| Monorepo + AppProject | 平台常见折中 | 需规范目录 |

## 推荐 Monorepo 布局

```
├── apps/                 # 业务应用
│   ├── frontend/
│   └── api/
├── infra/                # 集群级组件
│   ├── ingress-nginx/
│   └── cert-manager/
├── clusters/             # 集群 bootstrap（App of Apps）
│   ├── dev/
│   │   └── root-app.yaml
│   └── prod/
│       └── root-app.yaml
└── docs/
```

## 分支策略

| 策略 | 说明 |
|------|------|
| trunk-based | main 即 prod，tag 标记发布 |
| env 分支 | dev/staging/prod 分支（较少用） |
| overlay 目录 | main + overlays 区分环境（推荐） |

## Commit 规范

```
feat(api): bump image to v1.2.3
fix(frontend): increase memory limit prod overlay
chore(infra): upgrade prometheus chart 55.0.0
```

## .argocd-ignore（可选）

Repo Server 可配置忽略路径，加快渲染：

```
# 在 argocd-cm ConfigMap
reposerver.git.requestTimeout: 60s
```

## 权限与 CODEOWNERS

```
/apps/api/prod/     @team-api @sre-oncall
/infra/             @platform-team
```

## 与 CI 分工

```
CI 仓库：Dockerfile、源码、单元测试
CD 仓库（GitOps）：K8s Manifest、Helm values、image tag
```

CI 构建完 **只改 CD 仓 image tag**，不直接 kubectl。

## 反模式

- Manifest 与源码混仓无目录规范
- 二进制、大文件进 Git
- 无 CODEOWNERS prod 目录人人可改

下一篇：**健康检查**与资源状态解读。
