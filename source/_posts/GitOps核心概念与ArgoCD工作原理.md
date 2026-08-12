---
title: GitOps 核心概念与 Argo CD 工作原理
date: 2026-08-26 09:15:00
tags:
  - ArgoCD
  - GitOps
  - 入门
categories:
  - ArgoCD 新手入门
---

理解 GitOps 三原则，是正确使用 Argo CD 的前提。

## GitOps 三原则

| 原则 | 含义 |
|------|------|
| 声明式 | 用 YAML 描述期望状态，而非脚本命令 |
| 版本化 | 所有配置存在 Git，可审计、可回滚 |
| 自动拉取 | 控制器主动 Reconcile，而非 CI push 到集群 |

## Argo CD Reconcile 循环

```
1. Repo Server 从 Git 拉取 Manifest
2. 渲染（Plain / Kustomize / Helm）
3. 与集群 Live State 对比（diff）
4. Sync：Apply 差异到集群
5. 健康检查：Deployment/Pod 是否 Ready
6. 周期性重复（默认 3 分钟）
```

## 三种同步方式

| 方式 | 说明 |
|------|------|
| Manual | 人工点 Sync（新手推荐） |
| Auto | Git 变更自动部署 |
| Self Heal | 集群被 kubectl 改了，自动改回 Git 状态 |

## Pull vs Push 模型

```
Push（传统 CI/CD）：
  CI → kubectl apply → K8s
  问题：CI 需集群凭证，安全风险

Pull（GitOps / Argo CD）：
  Git → Argo CD（在集群内）→ K8s
  优势：集群凭证不出集群
```

## 状态术语

| 状态 | 含义 |
|------|------|
| Synced | Git 与集群一致 |
| OutOfSync | 有差异，待 Sync |
| Healthy | 资源运行正常 |
| Degraded | 资源异常（如 Pod CrashLoop） |
| Progressing | 正在滚动更新 |

## 典型工作流

```
1. 开发改代码 → CI 构建镜像 push registry
2. 运维/开发改 Git 中 image tag
3. Argo CD 检测 OutOfSync
4. Sync → 集群滚动更新
5. UI 确认 Healthy
```

## 反模式

- Git 与集群双源真相（有人 kubectl edit）
- Auto Sync + 未 Review 直接合 main
- Manifest 与镜像构建混在同一 Pipeline 无 Git 记录

下一篇：**安装 Argo CD** 并部署第一个 Application。
