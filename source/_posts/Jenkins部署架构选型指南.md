---
title: Jenkins 部署架构选型指南
date: 2026-08-23 09:15:00
tags:
  - Jenkins
  - 架构
categories:
  - Jenkins SRE
---

Jenkins 架构选型取决于团队规模、构建类型与是否上 K8s。

## 常见架构

| 架构 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| 单机 All-in-One | POC/小团队 | 简单 | 无 HA、资源争用 |
| Controller + 静态 Agent | 中型 | 稳定 | Agent 利用率低 |
| Controller HA + NFS/EFS | 生产 | 高可用 | 共享存储依赖 |
| K8s 动态 Agent | 云原生 | 弹性、隔离 | 插件/镜像维护 |
| 云托管（CloudBees 等） | 免运维 | 企业特性 | 成本 |

## 组件

```
Developer → Git Webhook → Jenkins Controller
                              ↓ 调度
                         Agent Pool（VM/K8s Pod/Docker）
                              ↓
                         Artifact Registry / K8s Deploy
```

## Agent 类型

| 类型 | 场景 |
|------|------|
| 永久 Agent | 稳定、大缓存构建 |
| SSH Agent | 远程 VM |
| Docker Agent | 容器化构建 |
| K8s Pod Agent | 弹性、多租户隔离 |

## 选型决策

```
构建并发 < 20，无 K8s？
  ├─ 是 → Controller HA + 3~5 静态 Agent
  └─ 否 → K8s Plugin 动态 Pod Agent
```

## 与 GitOps 分工

| Jenkins | Argo CD/Flux |
|---------|--------------|
| 构建、测试、打镜像 | Git 声明式部署 |
| 复杂 Pipeline | 集群状态同步 |

## 版本

- 生产推荐 **Jenkins LTS**（如 2.440.x LTS）
- JDK 17（Jenkins 2.357+ 要求）

架构文档应包含：Controller HA 方案、JENKINS_HOME 存储、Agent 池规划、网络拓扑。
