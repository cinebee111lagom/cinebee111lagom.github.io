---
title: Argo CD Application 同步策略与 Sync Policy
date: 2026-08-26 10:30:00
tags:
  - ArgoCD
  - Sync
  - 入门
categories:
  - ArgoCD 新手入门
---

Sync Policy 决定 **何时同步、如何处理漂移、如何清理资源**。

## syncPolicy 结构

```yaml
spec:
  syncPolicy:
    automated:          # 可选：自动同步
      prune: true       # 删除 Git 中已移除的资源
      selfHeal: true    # 集群被改则自动改回
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PruneLast=true
      - ApplyOutOfSyncOnly=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

## 策略组合建议

| 环境 | automated | selfHeal | prune |
|------|-----------|----------|-------|
| dev | ✅ | ✅ | ✅ |
| staging | ✅ | ✅ | ⚠️ 谨慎 |
| prod | ❌ 手动 | ✅ | ❌ 或审批 |

生产 **Auto Sync** 需配合 PR Review 与分支保护。

## 常用 syncOptions

| 选项 | 作用 |
|------|------|
| CreateNamespace=true | 自动创建目标 namespace |
| PruneLast=true | 先创建新资源再删旧资源 |
| ApplyOutOfSyncOnly=true | 只 apply 差异部分 |
| ServerSideApply=true | 使用 SSA 避免 field manager 冲突 |
| RespectIgnoreDifferences=true | 忽略 diff 配置项 |

## 手动 Sync 参数

```bash
argocd app sync my-app --prune --force
argocd app sync my-app --dry-run
```

## Sync Waves（部署顺序）

用 annotation 控制资源创建顺序：

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"
```

```
wave -1: Namespace
wave  0: ConfigMap / Secret
wave  1: Deployment
wave  2: Ingress
```

## Hooks

PreSync / PostSync / SyncFail 用 Job 做迁移或验证。

## 反模式

- prod 开 prune 误删 CRD 依赖资源
- selfHeal 与 HPA 手动调 replicas 冲突（需 ignoreDifferences）
- 无 retry 导致短暂网络失败即失败

下一篇：**多环境** Dev/Staging/Prod 目录结构。
