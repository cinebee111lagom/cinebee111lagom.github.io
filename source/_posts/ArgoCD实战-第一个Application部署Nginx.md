---
title: Argo CD 实战：第一个 Application 部署 Nginx
date: 2026-08-26 10:15:00
tags:
  - ArgoCD
  - 实战
  - 入门
categories:
  - ArgoCD 新手入门
---

手把手完成 **Git → Argo CD → Nginx Running** 全流程。

## 1. 准备 Git 仓库

```
my-k8s-manifests/
└── nginx/
    ├── deployment.yaml
    └── service.yaml
```

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  selector:
    app: nginx
  ports:
    - port: 80
```

## 2. 注册仓库

```bash
argocd repo add https://github.com/<you>/my-k8s-manifests.git \
  --username git --password <github-token>
```

## 3. 创建 Application

```bash
kubectl create namespace demo

argocd app create nginx-demo \
  --project default \
  --repo https://github.com/<you>/my-k8s-manifests.git \
  --path nginx \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace demo \
  --sync-policy manual
```

## 4. 同步部署

```bash
argocd app sync nginx-demo
argocd app wait nginx-demo --health
kubectl get pods -n demo
```

## 5. 验证 GitOps

```bash
# 改 Git：replicas 2 → 3，commit push
argocd app get nginx-demo   # 应显示 OutOfSync
argocd app sync nginx-demo
kubectl get deploy nginx -n demo -o jsonpath='{.spec.replicas}'
```

## 6. UI 查看

打开 Argo CD UI → Applications → nginx-demo，可见资源树与 Sync 状态。

## 检查点

| 步骤 | 期望 |
|------|------|
| repo add | Successful |
| app create | 无报错 |
| sync | Synced + Healthy |
| Git 变更 | OutOfSync → Sync 后一致 |

## 反模式

- path 写错导致 Empty sync
- 忘记 create namespace
- dest-namespace 与 YAML 内 namespace 冲突

这是后续 Helm、多环境、Auto Sync 的基础练习。
