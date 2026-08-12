---
title: Jenkins SRE 入门：生产部署职责与目标
date: 2026-08-23 09:00:00
tags:
  - Jenkins
  - SRE
categories:
  - Jenkins SRE
---

Jenkins 是企业 CI/CD 的核心枢纽，SRE 目标是让构建平台在**可用性、安全、构建吞吐**下长期稳定运行。

## SRE 职责

| 领域 | 内容 |
|------|------|
| 部署 | Controller HA、Agent 池、K8s 插件 |
| 高可用 | 主备、共享 JENKINS_HOME、负载均衡 |
| 备份 | 配置、Job、凭据、插件版本快照 |
| 容量 | Agent 数、Executor、磁盘、构建队列 |
| 可观测 | 构建成功率、队列时长、Agent 离线 |
| 变更 | 升级、插件审批、Pipeline 模板 |
| 安全 | RBAC、凭据、CSRF、网络隔离 |
| 标准化 | 共享库、Golden Pipeline |

## 生产 SLA 参考

| 指标 | 目标 |
|------|------|
| Controller 可用性 | 99.9% ~ 99.95% |
| 构建排队 P95 | < 5 分钟（常规 Job） |
| 构建失败率（非业务） | < 1%（平台原因） |
| RPO | ≤ 24h（日备份 JENKINS_HOME） |
| RTO | ≤ 1h（从备份恢复） |

## 架构演进

```
单机 Jenkins → Controller + 静态 Agent
            → Controller HA + 共享存储
            → K8s 动态 Agent（Kubernetes Plugin）
            → 与 GitOps/Argo CD 分工协作
```

## 与开发、平台的边界

- **开发**：Jenkinsfile、单元测试、构建逻辑
- **SRE/平台**：Controller 运维、Agent 池、备份、升级、RBAC
- **安全**：凭据审批、插件白名单、审计

本系列 20 篇覆盖 Jenkins 从部署、HA、Pipeline、Agent、监控到容灾演练的完整 SRE 路径。
