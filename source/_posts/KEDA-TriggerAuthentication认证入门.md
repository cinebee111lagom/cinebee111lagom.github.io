---
title: KEDA TriggerAuthentication 认证入门
date: 2026-09-09 09:20:00
tags:
  - KEDA
  - 认证
  - 入门
categories:
  - KEDA 新手入门
---

把鉴权从 ScaledObject 中拆出，便于复用与由平台团队统一管理。

## 常见来源

| 方式 | 说明 |
|------|------|
| secretTargetRef | 引用 K8s Secret |
| env | 从目标容器环境变量取 |
| podIdentity | 云厂商身份（AWS/Azure/GCP 等） |
| HashiCorp Vault / Azure Key Vault | 外部密钥库 |
| OAuth2 | clientCredentials 拉 token |

跨命名空间用 **ClusterTriggerAuthentication**。ScaledObject 的 trigger 通过 `authenticationRef` 引用。

> 官方文档（v2.20）：[Authentication](https://keda.sh/docs/2.20/concepts/authentication/)

