---
title: Argo CD Sync 失败与 OutOfSync 生产排查
date: 2026-08-27 12:00:00
tags:
  - ArgoCD
  - SRE
  - 排查
categories:
  - ArgoCD SRE
---

生产值班最高频：**Sync Failed** 与 **长期 OutOfSync**。

## Sync Failed 分类

| 阶段 | 错误类型 | 日志位置 |
|------|----------|----------|
| Git Fetch | 401/404/timeout | repo-server |
| Render | helm/kustomize error | repo-server |
| Apply | RBAC/Quota/CRD | application-controller |
| Hook | PreSync Job 失败 | app events |

```bash
argocd app get my-app --show-operation
kubectl logs -n argocd deploy/argocd-repo-server --tail=100 | grep my-app
kubectl logs -n argocd statefulset/argocd-application-controller --tail=100
```

## OutOfSync 生产原因

| 原因 | 处理 |
|------|------|
| 人工 kubectl edit | Sync + 开 selfHeal |
| HPA 改 replicas | ignoreDifferences |
| Mutating Webhook 注入 sidecar | ignore 或 Git 纳入 |
| 字段默认值漂移 | ServerSideApply |
| compareOptions ignoreAggregatedRoles | ClusterRole 聚合 |

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
  syncPolicy:
    syncOptions:
      - ServerSideApply=true
```

## 批量 OutOfSync 事件

```
Git 凭证过期 → 所有 app Failed/Unknown
CRD 升级     → 某类资源 Sync 失败
Argo CD 升级 → compare 逻辑变化
```

优先查 **repo-server 全局错误**。

## 应急

```bash
# 暂停自动 sync（防 prod 雪崩）
argocd app set my-app --sync-policy none

# 仅 dry-run 定位
argocd app sync my-app --dry-run --prune

# hard refresh 清缓存
argocd app get my-app --hard-refresh
```

## Runbook 决策树

```
Failed？
  Git → 凭证/branch/path
  Render → 本地 helm template
  Apply → kubectl describe + events

OutOfSync 但健康？
  diff → ignoreDifferences / 误改集群
```

## 反模式

- Force Sync 不查根因
- prod 批量 `--force` 无变更单
- ignoreDifferences 过宽掩盖真实漂移

建立 **Top 10 Sync 错误** 内部知识库。
