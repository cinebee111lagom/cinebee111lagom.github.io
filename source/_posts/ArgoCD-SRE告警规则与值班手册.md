---
title: ArgoCD SRE 告警规则与值班手册
date: 2026-08-27 10:15:00
tags:
  - ArgoCD
  - SRE
  - 告警
categories:
  - ArgoCD SRE
---

## P0 告警

```yaml
- alert: ArgoCDDown
  expr: up{job="argocd-server-metrics"} == 0
  for: 5m

- alert: ArgoCDControllerDown
  expr: up{job="argocd-application-controller-metrics"} == 0
  for: 5m

- alert: ArgoCDProdAppDegraded
  expr: argocd_app_info{health_status="Degraded",project="production"} == 1
  for: 5m

- alert: ArgoCDClusterDisconnected
  expr: argocd_cluster_connection_status == 0
  for: 2m
```

## P1 告警

```yaml
- alert: ArgoCDProdOutOfSync
  expr: argocd_app_info{sync_status="OutOfSync",project="production"} == 1
  for: 30m

- alert: ArgoCDSyncFailureRateHigh
  expr: rate(argocd_app_sync_total{phase="Failed"}[15m]) > 0.1
  for: 10m

- alert: ArgoCDGitFetchSlow
  expr: histogram_quantile(0.99, rate(argocd_git_request_duration_seconds_bucket[5m])) > 60
  for: 15m

- alert: ArgoCDRedisDown
  expr: up{job="argocd-redis-ha"} == 0
  for: 5m
```

## 值班 Runbook

| 告警 | 第一步 | 第二步 |
|------|--------|--------|
| ArgoCDDown | kubectl get pods -n argocd | Ingress/DNS/证书 |
| Prod Degraded | argocd app get \<app\> | Pod/Event 日志 |
| OutOfSync | argocd app diff | ignoreDifferences / 误改集群 |
| Sync Failed | repo-server 日志 | Git 凭证/path/helm render |
| Cluster Disconnected | cluster secret | 网络/API 证书过期 |

## 通知路由

```
P0 → 电话 + IM + 工单（5 分钟）
P1 → IM + 工单（30 分钟）
staging 告警 → 仅 IM（工作日）
```

## 反模式

- prod 与 dev 告警同路由
- 告警无 Runbook 链接
- OutOfSync 阈值过短（未合并 PR 即告警）

每季度演练：**模拟 controller pod 故障 + prod app Degraded**。
