---
title: Argo CD 与 CI/CD 流水线配合入门
date: 2026-08-26 13:00:00
tags:
  - ArgoCD
  - CI/CD
  - 入门
categories:
  - ArgoCD 新手入门
---

GitOps 下 CI 负责 **构建**，CD 由 Argo CD 负责 **部署**。

## 标准流水线

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Code   │ →  │   CI    │ →  │   Git   │ →  │ Argo CD │
│  Push   │    │ Build   │    │ Update  │    │  Sync   │
└─────────┘    └─────────┘    │  tag    │    └─────────┘
                               └─────────┘
```

## GitHub Actions 示例

```yaml
name: CI and Update Manifest
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push
        run: |
          docker build -t registry.io/myapp:${{ github.sha }} .
          docker push registry.io/myapp:${{ github.sha }}

      - name: Update GitOps repo
        run: |
          git clone https://github.com/myorg/k8s-manifests.git
          cd k8s-manifests
          sed -i "s/newTag:.*/newTag: ${GITHUB_SHA}/" \
            apps/myapp/overlays/dev/kustomization.yaml
          git commit -am "ci: bump myapp to ${GITHUB_SHA}"
          git push

      - name: Trigger Argo CD sync
        run: |
          argocd login argocd.example.com --username ci --password ${{ secrets.ARGOCD_TOKEN }} --grpc-web
          argocd app sync myapp-dev --timeout 300
          argocd app wait myapp-dev --health --timeout 600
```

## CI 与 Argo CD 职责边界

| CI | Argo CD |
|----|---------|
| 单元测试 | Deploy |
| 镜像构建扫描 | 健康检查 |
| 更新 image tag | Diff/Reconcile |
| 触发 sync（可选） | 漂移修复 |

## 镜像更新工具

| 工具 | 说明 |
|------|------|
| 手写 sed | 简单 |
| [Argo CD Image Updater](https://github.com/argoproj-labs/argocd-image-updater) | 自动跟踪 registry tag |
| Kustomize images 字段 | 最常用 |

Image Updater 适合 **dev 自动跟踪 latest**，prod 仍建议 PR。

## Jenkins 集成

```groovy
stage('Deploy') {
  steps {
    sh 'argocd app sync myapp --grpc-web'
    sh 'argocd app wait myapp --health --timeout 600'
  }
}
```

## 反模式

- CI 里 kubectl apply 绕过 Argo CD
- CI 账号用 admin
- 不 wait health 就标记部署成功

下一篇：**HA 部署**入门。
