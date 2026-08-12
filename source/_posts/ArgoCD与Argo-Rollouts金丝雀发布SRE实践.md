---
title: Argo CD 与 Argo Rollouts 金丝雀发布 SRE 实践
date: 2026-08-27 12:45:00
tags:
  - ArgoCD
  - SRE
  - Rollouts
categories:
  - ArgoCD SRE
---

**Argo CD** 管「部署什么」，**Argo Rollouts** 管「怎么渐进发布」，生产常配合使用。

## 分工

```
Git Manifest（含 Rollout CR）
    → Argo CD Sync
    → Argo Rollouts Controller 执行 Canary/BlueGreen
    → Prometheus/Analysis 自动晋升或回滚
```

## Rollout 示例

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 5
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 5m}
        - setWeight: 100
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 1
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: registry.io/myapp:v2
```

Argo CD Application 指向含 Rollout 的 path，Sync 后 Rollouts controller 接管。

## AnalysisTemplate（Prometheus）

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.99
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(http_requests_total{status=~"2..",app="myapp"}[2m]))
            / sum(rate(http_requests_total{app="myapp"}[2m]))
```

## SRE 关注点

| 项 | 说明 |
|----|------|
| 两个 controller | CD + Rollouts 都要 HA |
| Git 变更 | image tag 变更触发新 Rollout |
| 回滚 | Rollouts abort 或 Git revert |
| 监控 | Rollout phase、analysis 结果告警 |

## 告警

```yaml
- alert: RolloutDegraded
  expr: rollout_info{phase="Degraded"} == 1
  for: 5m
```

## 反模式

- Argo CD Auto Sync 在 Canary 中途又 Sync 旧 manifest
- 无 Analysis 纯 manual pause
- Rollouts controller 单副本生产

金丝雀发布策略应在 **Git 中版本化**，与 Argo CD 多环境 overlay 配合。
