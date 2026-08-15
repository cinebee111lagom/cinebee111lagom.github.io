---
title: Volcano 文档：安装指南
date: 2026-09-10 09:10:00
tags:
  - Volcano
  - 安装
categories:
  - Volcano 文档导读
---

要求：Kubernetes ≥ 1.13，支持 CRD。

## 三种方式

**YAML：**

```shell
kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/master/installer/volcano-development.yaml
```

可将 `master` 换成 release 分支或版本 tag。

**源码本地：**

```shell
git clone https://github.com/volcano-sh/volcano.git
cd volcano && ./hack/local-up-volcano.sh
```

**Helm：**

```shell
helm repo add volcano-sh https://volcano-sh.github.io/helm-charts
helm install volcano volcano-sh/volcano -n volcano-system --create-namespace
```

验证：`kubectl get all -n volcano-system`（admission / controllers / scheduler Ready）。

> 官方文档：[Installation](https://volcano.sh/zh-Hans/docs/GettingStarted/Installation)

