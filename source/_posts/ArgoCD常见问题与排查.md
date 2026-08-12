---
title: Argo CD 常见问题与排查
date: 2026-08-26 13:30:00
tags:
  - ArgoCD
  - 排查
  - 入门
categories:
  - ArgoCD 新手入门
---

GitOps 值班常见问题与 **第一步排查命令**。

## 同步失败

| 现象 | 排查 |
|------|------|
| repository not accessible | `argocd repo get <url>` 测凭证 |
| path not found | 确认 Git path 与分支 |
| helm template error | 本地 `helm template` 复现 |
| kustomize build error | `kubectl kustomize <path>` |
| permission denied | destination namespace RBAC |

```bash
argocd app get my-app
kubectl logs -n argocd deploy/argocd-repo-server --tail=100
kubectl logs -n argocd statefulset/argocd-application-controller --tail=100
```

## OutOfSync 但 Git 未改

| 原因 | 解决 |
|------|------|
| 集群被 kubectl 修改 | Sync 或开 selfHeal |
| 字段被 K8s 默认值填充 | ignoreDifferences |
| HPA 改 replicas | ignore Deployment /replicas |
| Mutating Webhook 注入 | ignore 或统一 Git |

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```

## Degraded / Pod 不健康

```bash
argocd app resources my-app --kind Pod
kubectl describe pod <pod> -n <ns>
kubectl logs <pod> -n <ns>
```

常见：ImagePullBackOff、CrashLoop、资源不足。

## 性能慢

| 原因 | 解决 |
|------|------|
| 大 repo | shallow clone、monorepo 拆分 |
| 大 helm chart | repo-server 扩容 |
| 过多 Application | ApplicationSet + sharding |

## CLI / UI 登录失败

```bash
kubectl get pods -n argocd
kubectl logs -n argocd deploy/argocd-server
argocd account update-password  # 重置
```

## 对比缓存问题

```bash
argocd app get my-app --hard-refresh
```

## 排查流程图

```
Sync 失败？
  ├─ repo 错误 → 凭证/path
  ├─ render 错误 → 本地 helm/kustomize
  └─ apply 错误 → kubectl describe / events

Synced 但 Degraded？
  └─ Pod/Event 日志

一直 OutOfSync？
  └─ diff → ignoreDifferences
```

## 反模式

- 不读 repo-server 日志盲目重试 Sync
- Force Sync 掩盖 Git 错误
- 生产直接改 Live 集群

收藏本文作为 **GitOps 值班速查**。
