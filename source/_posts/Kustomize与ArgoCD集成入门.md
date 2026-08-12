---
title: Kustomize 与 Argo CD 集成入门
date: 2026-08-26 11:00:00
tags:
  - ArgoCD
  - Kustomize
  - 入门
categories:
  - ArgoCD 新手入门
---

Argo CD **原生支持 Kustomize**，无需额外插件。

## Application 配置

```yaml
spec:
  source:
    repoURL: https://github.com/myorg/k8s-manifests.git
    targetRevision: main
    path: apps/myapp/overlays/prod
    # 默认自动检测 kustomization.yaml，也可显式指定：
    # kustomize:
    #   images:
    #     - myapp=registry.io/myapp:v2.0
```

Argo CD 内置 Kustomize 版本可在 Settings 查看。

## 常用 Kustomize 能力

| 能力 | 用途 |
|------|------|
| resources | 组合多个 YAML |
| images | 改镜像 tag |
| patches |  strategic merge / JSON6902 |
| configMapGenerator | 生成 ConfigMap |
| namespace | 统一命名空间 |
| commonLabels | 追加标签 |

## 镜像 tag 更新（CI 常见）

```yaml
# kustomization.yaml
images:
  - name: registry.io/myapp
    newTag: v1.2.3
```

CI 只需 sed/commit 改 `newTag`，Argo CD 检测 OutOfSync。

## 预览渲染结果

```bash
argocd app manifests my-app
kubectl kustomize apps/myapp/overlays/prod
```

两者应一致（Argo CD 可能带额外 label）。

## helm vs kustomize 选型

| | Kustomize | Helm |
|---|-----------|------|
| 学习曲线 | 低（纯 YAML） | 中（模板） |
| 复用 | overlay 组合 | chart 参数 |
| 社区 chart | 少 | 多（如 prometheus） |
| Argo CD | 原生 | 原生 |

微服务自有 Manifest 推荐 **Kustomize**；第三方中间件推荐 **Helm**。

## 反模式

- overlay 里改 base 文件（应 patch）
- 不用 kustomization.yaml 直接放裸 YAML 难维护
- images 字段 name 与 deployment 中 image 不匹配

下一篇：**Helm 与 Argo CD 集成**。
