---
title: Argo CD 新手学习路径与入门 Checklist
date: 2026-08-26 13:45:00
tags:
  - ArgoCD
  - 入门
  - 学习路径
categories:
  - ArgoCD 新手入门
---

## 推荐学习路径

```
第 1 周：概念 + 安装 + 第一个 Application
  └─ 篇 1~6

第 2 周：Sync Policy + 多环境 + Kustomize/Helm
  └─ 篇 7~11

第 3 周：健康检查 + 回滚 + Secret + RBAC
  └─ 篇 12~15

第 4 周：UI + CI/CD + HA + 排查
  └─ 篇 16~19

第 5 周：综合实战 + Checklist 验收
  └─ 篇 20
```

## 入门 Checklist

### 基础

- [ ] K8s 集群可用，kubectl 正常
- [ ] Argo CD 安装，UI 与 CLI 可登录
- [ ] 理解 Application / Project / Repository
- [ ] 完成 Nginx Application 部署实战
- [ ] 会 `argocd app sync / diff / get`

### GitOps 工作流

- [ ] Git 仓库存 Manifest，变更触发 OutOfSync
- [ ] 理解 Manual vs Auto Sync、selfHeal、prune
- [ ] 会用 Kustomize overlay 管理 dev/prod
- [ ] 会用 Helm 部署至少一个 chart
- [ ] 完成一次 Git revert 回滚

### 安全与多租户

- [ ] Secret 不进 Git（Sealed Secrets 或 External Secrets）
- [ ] 创建至少一个 AppProject 限制 namespace
- [ ] 非 admin 账号可 sync dev 不可 sync prod

### 集成

- [ ] CI 构建镜像并更新 Git 中 image tag
- [ ] CI 或人工 sync 后 `app wait --health` 成功
- [ ] 能读 UI 资源树与 Diff

### 排查

- [ ] 会查 repo-server / controller 日志
- [ ] 会处理 OutOfSync（ignoreDifferences）
- [ ] 会处理 ImagePullBackOff / Degraded

## 配套练习

| 练习 | 技能点 |
|------|--------|
| 部署 guestbook 官方示例 | 熟悉 UI |
| dev→prod overlay 晋级 | 多环境 |
| 故意改集群触发 selfHeal | 漂移理解 |
| Sealed Secret 进 Git | 密钥管理 |
| GitHub Actions 改 tag + sync | CI/CD |

## 推荐资源

- [Argo CD 官方文档](https://argo-cd.readthedocs.io/)
- [argoproj/argocd-example-apps](https://github.com/argoproj/argocd-example-apps)
- [OpenGitOps 原则](https://opengitops.dev/)

## 延伸（后续可学）

- **ArgoCD SRE 系列**（告警、备份、多集群生产）
- **ApplicationSet** 批量应用管理
- **Argo Rollouts** 金丝雀/蓝绿发布
- **Jenkins SRE** 与 GitOps 分工

---

**ArgoCD 新手入门系列 20 篇**完结，从零到能独立用 GitOps 部署 K8s 应用。建议配合 **Kubernetes**、**Helm** 基础一起实践。
