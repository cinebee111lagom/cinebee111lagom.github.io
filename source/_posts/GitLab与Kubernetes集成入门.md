---
title: GitLab 与 Kubernetes 集成入门
date: 2026-08-28 12:45:00
tags:
  - GitLab
  - Kubernetes
  - 入门
categories:
  - GitLab 新手入门
---

GitLab 可通过 **Agent for Kubernetes** 或 **kubectl in CI** 连接 K8s 集群。

## 方式一：CI 中 kubectl deploy

```yaml
deploy-k8s:
  stage: deploy
  image:
    name: bitnami/kubectl:latest
    entrypoint: [""]
  script:
    - kubectl config use-context myorg/agent:my-cluster
    - kubectl set image deployment/myapp app=$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA -n prod
    - kubectl rollout status deployment/myapp -n prod
  environment:
    name: production
    url: https://myapp.example.com
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

需在 CI Variables 配置 `KUBECONFIG` 或使用 Agent。

## 方式二：GitLab Agent（推荐）

**Infrastructure → Kubernetes clusters → Connect a cluster**

```yaml
# .gitlab/agents/my-agent/config.yaml
gitops:
  manifest_projects:
    - id: mygroup/gitops-manifests
      default_namespace: default
ci_access:
  projects:
    - id: mygroup/my-api
```

Agent 在集群内运行，**无需暴露 API 到公网**。

## Environment 追踪

**Deployments → Environments**

每次 deploy Job 记录环境版本，可 **一键 Rollback**（GitLab UI）。

```yaml
deploy:
  environment:
    name: staging
    on_stop: stop-staging

stop-staging:
  stage: deploy
  script:
    - kubectl delete namespace staging-preview
  when: manual
  environment:
    name: staging
    action: stop
```

## 与 Argo CD 配合（GitOps）

```yaml
# CI 只更新 GitOps 仓 image tag，不直接 kubectl
update-gitops:
  script:
    - git clone git@gitlab.com:mygroup/gitops.git
    - sed -i "s/tag:.*/tag: $CI_COMMIT_SHA/" apps/myapp/prod/kustomization.yaml
    - git commit -am "deploy $CI_COMMIT_SHA" && git push
```

## 反模式

- CI 使用 cluster-admin kubeconfig
- 生产 deploy 无 environment 记录
- GitOps 与 kubectl apply 双轨

下一篇：**Webhook 与外部集成**。
