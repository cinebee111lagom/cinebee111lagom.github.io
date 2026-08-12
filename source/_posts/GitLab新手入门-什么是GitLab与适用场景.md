---
title: GitLab 新手入门：什么是 GitLab 与适用场景
date: 2026-08-28 09:00:00
tags:
  - GitLab
  - DevOps
  - 入门
categories:
  - GitLab 新手入门
---

**GitLab** 是基于 Git 的 DevOps 平台，将 **代码托管、CI/CD、Issue、Registry** 集成在一个产品中，适合团队从开发到交付的全流程协作。

## GitLab 能做什么

| 能力 | 说明 |
|------|------|
| Git 仓库 | 分支、MR、Code Review |
| CI/CD | `.gitlab-ci.yml` 流水线 |
| Container Registry | 内置 Docker 镜像仓 |
| Issue/Milestone | 需求与缺陷跟踪 |
| Wiki/Snippet | 文档与代码片段 |
| Pages | 静态站点托管 |
| K8s Agent | 与集群集成部署 |

## 与 GitHub 对比

| | GitHub | GitLab |
|---|--------|--------|
| CI/CD | Actions（YAML） | 内置 GitLab CI |
| 私有化 | Enterprise | CE/EE 自建 |
| Registry | GHCR | 内置 Registry |
| 一体化 | 需组合多工具 | 单平台 |
| 社区 | 最大 | 活跃 |

## 部署形态

| 形态 | 说明 |
|------|------|
| GitLab.com | SaaS，免费 tier |
| 自建 CE | 开源社区版，功能足够中小团队 |
| 自建 EE | 企业版，合规/高级安全 |

## 适用场景

**适合**：
- 希望 Git + CI/CD 一体的团队
- 需要私有化部署的企业
- DevOps 平台统一入口
- 与 K8s/Argo CD 配合的 GitOps 仓

**可考虑其他方案**：
- 纯开源协作 → GitHub
- 已有 Jenkins 且不愿迁移 → 仅作 Git 仓

## 核心概念预览

```
Project → Repository + CI/CD + Issues
Group   → 多 Project 组织与权限
Runner  → 执行 CI Job 的代理
Pipeline → 一次 CI 运行（含多个 Stage/Job）
MR      → Merge Request，代码合并请求
```

## 学习路线

```
账号/安装 → Git 推送 → MR 工作流 → .gitlab-ci.yml → Runner → Registry → K8s
```

本系列 20 篇从零带你掌握 GitLab 日常使用与 CI/CD 入门。
