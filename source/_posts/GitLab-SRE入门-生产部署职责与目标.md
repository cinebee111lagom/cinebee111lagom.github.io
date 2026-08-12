---
title: GitLab SRE 入门：生产部署职责与目标
date: 2026-08-29 09:00:00
tags:
  - GitLab
  - SRE
  - DevOps
categories:
  - GitLab SRE
---

GitLab 是团队 **代码与 CI/CD 中枢**，SRE 目标是保障其在**可用性、安全、性能**下 7×24 稳定服务全组织。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | Omnibus/K8s/Helm 架构、HA、Geo |
| 存储 | Gitaly、对象存储、备份 |
| CI/CD | Runner 池、队列、流水线 SLA |
| 数据库 | PostgreSQL、Redis 运维 |
| 可观测 | Prometheus、日志、审计 |
| 安全 | SSO、2FA、网络隔离、合规 |
| 变更 | 版本升级、零停机迁移 |
| 容量 | 用户/项目/Pipeline 并发规划 |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| GitLab Web/API 可用性 | 99.9% ~ 99.95% |
| git push/clone P99 | < 3s（常规仓） |
| Pipeline 调度延迟 | < 2 分钟（有 Runner） |
| MR/Review 不可用 | ≤ 15 分钟/月 |
| 备份 RPO | ≤ 24h（可更严） |
| 恢复 RTO | ≤ 4 小时 |

## 架构演进

```
单节点 Omnibus → 多节点组件分离 → HA（Patroni + Gitaly Cluster）
              → Geo 异地只读/灾备
              → GitLab Cloud（SaaS 外包 SRE）
```

## 与开发、平台的边界

- **开发**：项目结构、.gitlab-ci.yml、MR 流程
- **平台**：K8s、Registry 下游、Argo CD |
- **GitLab SRE**：实例运维、升级、备份、Runner 池、安全基线

本系列 20 篇覆盖 GitLab 从生产部署、监控、灾备到 CI 治理的完整 SRE 路径。
