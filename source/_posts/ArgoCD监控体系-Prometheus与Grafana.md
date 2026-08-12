---
title: Argo CD 监控体系：Prometheus 与 Grafana
date: 2026-08-27 10:00:00
tags:
  - ArgoCD
  - SRE
  - Prometheus
categories:
  - ArgoCD SRE
---

Argo CD 原生暴露 Prometheus 指标，SRE 需覆盖 **控制面 + 业务 Sync 状态**。

## 指标采集

```yaml
# ServiceMonitor（若用 Prometheus Operator）
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: argocd-metrics
  namespace: argocd
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-metrics
  endpoints:
    - port: metrics
```

组件 metrics 端口：

| 组件 | Service |
|------|---------|
| application-controller | argocd-application-controller-metrics |
| repo-server | argocd-repo-server-metrics |
| server | argocd-server-metrics |
| redis | redis-exporter（若启用） |

## 核心指标

| 指标 | 含义 |
|------|------|
| argocd_app_info | 应用元信息 |
| argocd_app_sync_total | Sync 次数 |
| argocd_app_reconcile_count | Reconcile 次数 |
| argocd_git_request_total | Git 请求 |
| argocd_git_request_duration_seconds | Git 延迟 |
| argocd_cluster_connection_status | 集群连通 |
| argocd_kubectl_exec_pending | 待执行操作队列 |

## Grafana Dashboard

官方 Dashboard ID：**14584**（Argo CD Operational Overview）

关键面板：

- Sync 成功率
- OutOfSync / Degraded 应用数
- Git fetch 延迟 P99
- Controller queue depth

## 日志

```bash
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller -f
kubectl logs -n argocd deploy/argocd-repo-server --tail=200
```

接入 Loki/ELK，保留 **audit log**（谁 sync 了 prod）。

## SLI 建议

| SLI | 计算 |
|-----|------|
| 控制面可用 | up{job="argocd-server"} |
| Sync 成功率 | sync_ok / sync_total |
| Git 可用 | git_request_failed_rate |
| 集群连通 | cluster_connection_status == 1 |

## 反模式

- 只监控 server 不监控 controller/repo-server
- 无 OutOfSync/Degraded 聚合告警
- audit log 未集中存储

监控上线标准：**prod Application Degraded 5 分钟内 P1**。
