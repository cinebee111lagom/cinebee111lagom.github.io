---
title: KEDA 运维 Operate 概览
date: 2026-09-09 10:40:00
tags:
  - KEDA
  - 运维
  - 入门
categories:
  - KEDA 新手入门
---

Operate 文档提供生产运行要求与指引（安全、集群操作、云事件等专题入口）。

## 运维清单

- [ ] 组件多副本与资源 request/limit
- [ ] 监控 Operator / Metrics / Webhook（Prometheus 或 OTel）
- [ ] 网络放行 metrics-apiserver（常 6443）与 webhook（9443）
- [ ] RBAC 最小权限读 Secret
- [ ] 升级前读 Migration / Release Note
- [ ] ScaledObject 备份入库（GitOps）

> 官方文档（v2.20）：[Operate](https://keda.sh/docs/2.20/operate/)

