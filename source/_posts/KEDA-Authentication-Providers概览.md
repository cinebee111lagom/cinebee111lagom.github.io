---
title: KEDA Authentication Providers 概览
date: 2026-09-09 10:30:00
tags:
  - KEDA
  - 认证
  - 入门
categories:
  - KEDA 新手入门
---

Authentication Providers 页面汇总各类鉴权扩展（OAuth2、云身份、Vault 等），与 `TriggerAuthentication` 配置段对应。

## 选型

| 环境 | 倾向 |
|------|------|
| 通用 K8s | Secret + TriggerAuthentication |
| 公有云 | Pod Identity / Workload Identity |
| 企业密钥中心 | Vault / Key Vault |
| API 需 token | OAuth2 clientCredentials |

凭证不要写在 ScaledObject `metadata` 明文里；用 `authenticationRef`。

> 官方文档（v2.20）：[Authentication Providers](https://keda.sh/docs/2.20/authentication-providers/)

