---
title: Argo CD 健康检查与资源状态解读
date: 2026-08-26 11:45:00
tags:
  - ArgoCD
  - 健康检查
  - 入门
categories:
  - ArgoCD 新手入门
---

Argo CD 为每种 K8s 资源定义 **Health** 逻辑，UI 颜色由此而来。

## 应用级状态

| 状态 | 含义 | 动作 |
|------|------|------|
| Healthy | 所有资源健康 | 无 |
| Progressing | 滚动更新中 | 等待 |
| Degraded | 有资源异常 | 排查 Pod/Event |
| Suspended | 暂停（如 CronJob suspend） | 视情况 |
| Missing | 资源不存在 | Sync 或检查 Git |

## 常见资源 Health 规则

| 资源 | Healthy 条件 |
|------|--------------|
| Deployment | Replica 全部 Ready |
| Pod | Phase=Running 且 Ready |
| Service | 存在即可（ClusterIP） |
| Ingress | LoadBalancer 有 address（云 LB） |
| PVC | Bound |
| Job | Succeeded |
| CRD 自定义 | 需 Lua health script |

## 查看详情

```bash
argocd app get my-app
argocd app resources my-app
kubectl describe pod -n my-ns
kubectl get events -n my-ns --sort-by='.lastTimestamp'
```

## 自定义 Health（Lua）

在 `argocd-cm` 为 CRD 配置：

```yaml
data:
  resource.customizations.health.mycompany.io_MyApp: |
    hs = {}
    if obj.status ~= nil and obj.status.ready == true then
      hs.status = "Healthy"
    else
      hs.status = "Progressing"
    end
    return hs
```

## Sync 成功 ≠ Healthy

```
Sync OK → 资源已 apply
Healthy → Pod 真正 Running

常见：镜像 pull 失败 → Synced 但 Degraded
```

## 等待健康

```bash
argocd app wait my-app --health --timeout 600
```

CI 应 wait health 再判定发布成功。

## 反模式

- 只看 Synced 不看 Pod 状态
- Ingress 无 LB 误判为平台问题（可能是云配额）
- CRD 无 custom health 永远 Unknown

下一篇：**回滚与历史版本**管理。
