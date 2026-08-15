---
title: KEDA Helm 部署入门
date: 2026-09-09 09:40:00
tags:
  - KEDA
  - Helm
  - 入门
categories:
  - KEDA 新手入门
---

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
kubectl get pods -n keda
```

卸载：

```bash
helm uninstall keda --namespace keda
```

若资源卡 finalizer：

```bash
kubectl patch scaledobject <name> -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch scaledjob <name> -p '{"metadata":{"finalizers":null}}' --type=merge
```

从旧版升级时注意 CRD 冲突，查阅官方 troubleshooting。

> 官方文档（v2.20）：[Deploy with Helm](https://keda.sh/docs/2.20/deploy/)

