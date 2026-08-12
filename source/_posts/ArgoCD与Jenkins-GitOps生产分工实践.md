---
title: Argo CD 与 Jenkins GitOps 生产分工实践
date: 2026-08-27 13:45:00
tags:
  - ArgoCD
  - SRE
  - Jenkins
categories:
  - ArgoCD SRE
---

多数企业 **Jenkins 做 CI，Argo CD 做 CD**，SRE 需明确边界与集成规范。

## 职责分工

| 阶段 | Jenkins | Argo CD |
|------|---------|---------|
| 编译测试 | ✅ | ❌ |
| 镜像构建扫描 | ✅ | ❌ |
| 更新 Git manifest | ✅（bot commit） | ❌ |
| 部署到 K8s | ❌（禁止 kubectl apply） | ✅ Sync |
| 漂移修复 | ❌ | ✅ selfHeal |
| 回滚 | 改 Git tag | Sync / revert |

## 标准流水线

```
Jenkins Pipeline:
  1. checkout code
  2. unit test
  3. docker build & push
  4. clone gitops-repo
  5. update image tag in kustomization.yaml
  6. git commit & push
  7. argocd app sync myapp-prod --grpc-web
  8. argocd app wait myapp-prod --health
```

## Jenkins 凭证

| 凭证 | 权限 |
|------|------|
| GitOps repo | bot 仅写 manifests 路径 |
| Argo CD token | 仅 sync 指定 Application |
| Docker registry | push 权限 |

**禁止** Jenkins 使用 Argo CD admin。

## 与 Image Updater 对比

| | Jenkins 改 Git | Argo CD Image Updater |
|---|----------------|----------------------|
| 控制 | Pipeline 显式 | 自动跟踪 registry |
| 审计 | Jenkins build + Git commit | Updater 日志 |
| prod | 推荐 Jenkins + PR | 慎用自动 |

## 冲突避免

| 问题 | 解决 |
|------|------|
| Jenkins kubectl 与 Argo CD 打架 | 禁用 Jenkins 集群凭证 |
| 双写 manifest | 单一 GitOps 仓 |
| Sync 未 wait | Pipeline 必须 `app wait --health` |

## 可观测

- Jenkins：build 成功率、推送 Git 失败率
- Argo CD：Sync 成功率、部署耗时
- 关联：Git commit message 含 Jenkins build ID

## 反模式

- Jenkins 与开发者都可 kubectl apply prod
- GitOps 仓与 Jenkins 仓分离无 trace
- prod sync 无 wait，Jenkins 绿但 Pod CrashLoop

清晰分工是 **GitOps 落地组织** 关键，参见 Jenkins SRE 系列对照阅读。

---

**ArgoCD SRE 系列 20 篇**完结，覆盖生产部署、监控、安全、灾备与组织协作。建议配合 **ArgoCD 新手入门** 系列循序渐进。
