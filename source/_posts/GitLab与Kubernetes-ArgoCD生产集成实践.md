---
title: GitLab 与 Kubernetes、Argo CD 生产集成实践
date: 2026-08-29 13:45:00
tags:
  - GitLab
  - SRE
  - GitOps
categories:
  - GitLab SRE
---

生产常见链路：**GitLab CI 构建 → Registry → 更新 GitOps 仓 → Argo CD Sync**。

## 标准 GitOps 流水线

```yaml
stages:
  - build
  - deploy

build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

update-gitops:
  stage: deploy
  image: alpine/git
  script:
    - git clone https://oauth2:${GITOPS_TOKEN}@gitlab.example.com/platform/gitops.git
    - cd gitops
    - sed -i "s/newTag:.*/newTag: ${CI_COMMIT_SHA}/" apps/myapp/overlays/prod/kustomization.yaml
    - git config user.email "ci@example.com"
    - git commit -am "deploy myapp ${CI_COMMIT_SHA}"
    - git push
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  environment:
    name: production
```

## GitLab Agent for K8s

```yaml
# .gitlab/agents/prod-agent/config.yaml
ci_access:
  projects:
    - id: platform/myapp
gitops:
  manifest_projects:
    - id: platform/gitops
```

Agent 使 CI 无需 kubeconfig 出集群。

## 职责边界

| GitLab SRE | Argo CD SRE |
|------------|-------------|
| Runner/Registry | Sync/多集群 |
| CI 变量/模板 | Application/Project |
| Pipeline SLA | GitOps 漂移 |

## 密钥

| 密钥 | 存储 |
|------|------|
| GITOPS_TOKEN | Project Protected Variable |
| Registry | CI_REGISTRY_* 内置 |
| Argo CD | CI 专用 account token |

## 监控全链路

```
Pipeline success → GitOps commit → Argo CD Synced → Pod Healthy
```

任一环节断裂需 **联合 Runbook**。

## 反模式

- CI 直接 kubectl apply prod
- GitOps 仓与源码仓权限不分
- 无 `environment` 追踪部署历史

---

**GitLab SRE 系列 20 篇**完结，覆盖自建 GitLab 生产运维全流程。建议与 **ArgoCD SRE**、**GitLab 新手入门** 对照阅读。
