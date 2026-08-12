---
title: ArgoCD SRE 入门：生产部署职责与目标
date: 2026-08-27 09:00:00
tags:
  - ArgoCD
  - SRE
  - GitOps
categories:
  - ArgoCD SRE
---

Argo CD 是 K8s 持续交付控制面，SRE 的目标是让它在**可用性、安全、交付速度**之间长期稳定——支撑全组织 GitOps 发布。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | HA 安装、Ingress/TLS、Redis、Dex/SSO |
| 多集群 | 集群注册、凭证轮换、网络连通 |
| 安全 | RBAC、Project 隔离、Secret 方案、审计 |
| 可观测 | Prometheus 指标、Sync 失败告警、审计日志 |
| 容量 | Application 数量、repo-server 性能、sharding |
| 变更 | Argo CD 版本升级、Helm chart 升级 |
| 备份 | argocd-secret、Application CR、Redis |
| 治理 | ApplicationSet、syncWindow、审批策略 |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| Argo CD 控制面可用性 | 99.9% ~ 99.95% |
| Sync 失败发现时间 | ≤ 5 分钟 |
| prod 误发布 RTO | ≤ 15 分钟（Git revert + Sync） |
| 控制面故障 RTO | ≤ 30 分钟（HA failover） |
| 未授权 Sync 事件 | 0 |

## 与开发、平台的边界

- **开发**：应用 Manifest、Helm values、image tag PR
- **平台/K8s**：集群、Namespace、Quota、网络 |
- **ArgoCD SRE**：控制面、RBAC、监控告警、升级、Runbook

## 架构演进

```
单集群单副本 → HA + Ingress + SSO
            → 多集群 central Argo CD
            → ApplicationSet + Policy Engine
            → 与 Argo Rollouts / Image Updater 集成
```

本系列 20 篇覆盖 Argo CD 从生产部署、监控、告警到灾备演练的完整 SRE 路径。
