---
title: Dragonfly 参考：Manager 配置
date: 2026-09-08 14:10:00
tags:
  - Dragonfly
  - Manager
  - 配置
  - 参考
categories:
  - Dragonfly 进阶指南
---

Manager 配置覆盖数据库、Redis、控制台、JWT/鉴权、集群相关参数等。

## 建议

- 用 Helm values 管理，勿手工改热 Pod 后丢失
- 密钥走 Secret
- 变更后验证 Console 登录与 Job API

> 官方文档：[Manager config](https://d7y.io/docs/next/reference/configuration/manager/)

