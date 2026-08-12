---
title: Helm 与 Argo CD 集成入门
date: 2026-08-26 11:15:00
tags:
  - ArgoCD
  - Helm
  - 入门
categories:
  - ArgoCD 新手入门
---

Helm Chart 是部署 **Prometheus、Ingress、中间件** 的常用方式，Argo CD 原生渲染 Helm。

## Application 引用 Helm

```yaml
spec:
  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: kube-prometheus-stack
    targetRevision: 55.0.0
    helm:
      releaseName: prometheus
      valueFiles:
        - values-prod.yaml
      parameters:
        - name: grafana.enabled
          value: "true"
```

## Git 仓内 Chart

```yaml
spec:
  source:
    repoURL: https://github.com/myorg/charts.git
    path: charts/myapp
    targetRevision: main
    helm:
      valueFiles:
        - values.yaml
```

path 指向含 `Chart.yaml` 的目录。

## values 文件管理

```
charts/myapp/
├── Chart.yaml
├── templates/
├── values.yaml          # 默认
└── values-prod.yaml     # 生产覆盖
```

```yaml
helm:
  valueFiles:
    - values.yaml
    - values-prod.yaml
```

## CLI 创建

```bash
argocd app create prometheus \
  --repo https://prometheus-community.github.io/helm-charts \
  --helm-chart kube-prometheus-stack \
  --revision 55.0.0 \
  --dest-namespace monitoring \
  --helm-set grafana.enabled=true
```

## 预览

```bash
argocd app manifests prometheus | head -50
helm template prometheus ./charts/myapp -f values-prod.yaml
```

## Helm + Kustomize 组合

可用 Kustomize 的 `helmCharts` 字段（Kustomize v4+），Argo CD 同样支持。

## 版本 pin

**务必 pin chart version**（targetRevision），避免 `*` 导致不可预期升级。

## 反模式

- values 含明文 Secret（用 Sealed Secrets / External Secrets）
- chart 版本不 pin
- releaseName 冲突导致覆盖他人 Release

Helm 适合平台组件；业务应用仍推荐 Kustomize + 自有 YAML。
