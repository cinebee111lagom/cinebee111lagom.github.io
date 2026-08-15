---
title: KEDA 部署方式概览
date: 2026-09-09 09:30:00
tags:
  - KEDA
  - 部署
  - 入门
categories:
  - KEDA 新手入门
---

要求：**Kubernetes ≥ 1.30**。

| 方式 | 适合 |
|------|------|
| Helm | 生产首选，易定制升级 |
| Operator Hub / OLM | OpenShift 等一键运维 |
| YAML 清单 | 强管控、无 Helm 环境 |
| MicroK8s | 本地试验 |

选型原则：要 values 治理用 Helm；要最简安装用 Operator Hub；要完全可控用 YAML。

> 官方文档（v2.20）：[Deploy](https://keda.sh/docs/2.20/deploy/)

