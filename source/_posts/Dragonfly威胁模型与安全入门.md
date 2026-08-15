---
title: Dragonfly 威胁模型与安全入门
date: 2026-09-07 12:50:00
tags:
  - Dragonfly
  - 安全
  - 入门
categories:
  - Dragonfly 新手入门
---

上线前应阅读官方 **Threat Model**，明确信任边界。

## 常见关注点

| 面 | 风险 |
|----|------|
| Peer 间传输 | 篡改、窃听 → TLS/鉴权 |
| Proxy 入口 | 未授权滥用成开放代理 |
| 控制面 | Manager API / Console 暴露 |
| 供应链 | 恶意制品被加速分发 |

## 基线

- 组件间 mTLS 或内网隔离
- Proxy 仅对集群节点开放
- RBAC 与审计（Manager 场景）

> 官方文档：[Threat Model](https://d7y.io/docs/next/operations/security/threat-model/)

