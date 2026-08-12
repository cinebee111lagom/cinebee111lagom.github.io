---
title: ArgoCD 新手入门：什么是 ArgoCD 与适用场景
date: 2026-08-26 09:00:00
tags:
  - ArgoCD
  - GitOps
  - 入门
categories:
  - ArgoCD 新手入门
---

**Argo CD** 是 CNCF 毕业项目，Kubernetes 上最流行的 **GitOps 持续交付**工具——以 Git 为唯一事实来源，自动将集群状态同步到期望状态。

## Argo CD 能做什么

| 能力 | 说明 |
|------|------|
| 自动同步 | Git 变更 → 自动部署到 K8s |
| 可视化 | UI 展示应用拓扑与健康状态 |
| 多集群 | 一个 Argo CD 管理多个 K8s 集群 |
| 回滚 | 基于 Git 历史或部署历史一键回滚 |
| 差异对比 | Live vs Desired 实时 diff |
| 权限 | Project + RBAC 多租户隔离 |

## GitOps 核心理念

```
开发者/运维 → 提交 Manifest 到 Git
                    ↓
              Argo CD 监听变更
                    ↓
              自动/手动 Sync 到 K8s
                    ↓
              持续 Reconcile（漂移检测）
```

**原则**：集群里改的不算数，Git 里写的才算数。

## 与 CI/CD 工具对比

| | Jenkins / GitHub Actions | Argo CD |
|---|--------------------------|---------|
| 触发 | Pipeline 脚本 | Git commit |
| 部署方式 | kubectl/helm apply | 声明式 Reconcile |
| 漂移检测 | 无（除非额外工具） | 内置 |
| 可视化 | 需自建 | 原生 UI |
| 回滚 | 重新跑 Pipeline | Git revert 或 History |

Argo CD 管 **CD（交付）**，CI 仍负责构建镜像。

## 适用场景

**适合**：
- K8s 微服务持续部署
- 多环境（dev/staging/prod）Git 管理
- 平台团队统一应用交付
- 合规审计（Git 即变更记录）

**不适合**：
- 非 K8s 工作负载（VM、Serverless 需其他方案）
- 纯 CI 构建（应用 Argo CD 不管编译）
- 极简单机试验（kubectl 直接 apply 即可）

## 核心组件

| 组件 | 作用 |
|------|------|
| **Application Controller** | 监听 Git，执行 Sync |
| **Repo Server** | 拉取 Git、渲染 Helm/Kustomize |
| **API Server** | UI / CLI / API 入口 |
| **Redis** | 缓存与状态 |
| **Dex**（可选） | SSO 集成 |

## 学习路线

```
概念 → 安装 → 第一个 Application → Sync/回滚 → Helm/Kustomize → 多环境 → RBAC → 排查
```

本系列 20 篇从零带你掌握 Argo CD 日常使用与 GitOps 入门。
