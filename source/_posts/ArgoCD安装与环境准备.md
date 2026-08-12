---
title: Argo CD 安装与环境准备
date: 2026-08-26 09:30:00
tags:
  - ArgoCD
  - 安装
  - 入门
categories:
  - ArgoCD 新手入门
---

Argo CD 通常部署在 **K8s 集群内**，也可管理外部集群。

## 环境要求

| 项 | 要求 |
|----|------|
| Kubernetes | 1.25+（建议 1.28+） |
| kubectl | 已配置集群访问 |
| Git 仓库 | GitHub/GitLab/Bitbucket 等 |
| 资源 | 控制面约 2 CPU / 4Gi（小规模） |

## 快速安装（官方 Manifest）

```bash
# 创建命名空间
kubectl create namespace argocd

# 安装（固定版本示例）
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/v2.11.0/manifests/install.yaml

# 等待 Pod Ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

## 访问 UI

```bash
# 获取初始 admin 密码
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo

# 端口转发
kubectl port-forward svc/argocd-server -n argocd 8080:443

# 浏览器：https://localhost:8080  用户 admin
```

## 安装 CLI

```bash
# Linux
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/download/v2.11.0/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/

# 登录
argocd login localhost:8080 --username admin --password <pwd> --insecure
```

## Helm 安装（生产推荐）

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd -n argocd --create-namespace \
  --set server.service.type=LoadBalancer
```

## 验收 Checklist

- [ ] 所有 argocd namespace Pod Running
- [ ] UI 可登录
- [ ] `argocd version` 正常
- [ ] `argocd cluster list` 可见 in-cluster

## 反模式

- 生产用 `--insecure` 无 TLS
- admin 密码不轮换
- 与业务工作负载同 namespace 无资源隔离

安装完成后，添加 Git 仓库并创建第一个 Application。
