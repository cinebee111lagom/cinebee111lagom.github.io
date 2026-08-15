---
title: KEDA YAML 与 Operator Hub 部署入门
date: 2026-09-09 09:50:00
tags:
  - KEDA
  - 部署
  - 入门
categories:
  - KEDA 新手入门
---

## YAML（v2.20.0 示例）

```bash
# 含 admission webhooks
kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.20.0/keda-2.20.0.yaml
# 不含 webhooks
kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.20.0/keda-2.20.0-core.yaml
```

推荐 `--server-side` 管理 CRD/Webhook。

## Operator Hub

在 OLM/OpenShift 安装 KEDA Operator，并创建名为 `keda` 的 `KedaController`（命名空间 `keda`）。

## MicroK8s

启用 dns/helm3 后：`microk8s helm3 install keda kedacore/keda -n keda --create-namespace`。

> 官方文档（v2.20）：[Deploy](https://keda.sh/docs/2.20/deploy/)

