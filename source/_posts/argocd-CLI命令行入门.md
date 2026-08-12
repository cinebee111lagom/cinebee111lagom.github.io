---
title: argocd CLI 命令行入门
date: 2026-08-26 10:00:00
tags:
  - ArgoCD
  - CLI
  - 入门
categories:
  - ArgoCD 新手入门
---

CLI 是自动化与脚本化的基础，与 UI 能力对等。

## 登录与上下文

```bash
argocd login argocd.example.com --username admin --password xxx
argocd account get-user-info
argocd context
```

## Application 管理

```bash
# 列表
argocd app list

# 创建
argocd app create nginx-demo \
  --repo https://github.com/myorg/k8s-manifests.git \
  --path apps/nginx \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace demo

# 同步
argocd app sync nginx-demo

# 状态
argocd app get nginx-demo

# 差异
argocd app diff nginx-demo

# 删除
argocd app delete nginx-demo
```

## 历史与回滚

```bash
argocd app history nginx-demo
argocd app rollback nginx-demo <id>
```

## 仓库与集群

```bash
argocd repo add https://github.com/myorg/repo.git --username x --password y
argocd repo list

argocd cluster add my-cluster-context --name production
argocd cluster list
```

## 常用组合

```bash
# 等待同步完成
argocd app sync nginx-demo --timeout 300
argocd app wait nginx-demo --health --sync

# 批量同步
argocd app sync -l env=staging
```

## 输出格式

```bash
argocd app list -o wide
argocd app get nginx-demo -o yaml
argocd app manifests nginx-demo   # 渲染后的 YAML
```

## CI/CD 集成示例

```bash
# Pipeline 最后一步：触发 Sync 并等待
argocd app sync my-app --grpc-web
argocd app wait my-app --health --timeout 600
```

## 反模式

- CI 中硬编码 admin 密码
- 不用 `--grpc-web` 穿透 Ingress 导致失败
- 脚本不 `wait` 就判定部署成功

CLI 熟练后，可完全脱离 UI 做 GitOps 自动化。
