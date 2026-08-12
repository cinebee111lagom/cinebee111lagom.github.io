---
title: GitLab 新手学习路径与入门 Checklist
date: 2026-08-28 13:45:00
tags:
  - GitLab
  - 入门
  - 学习路径
categories:
  - GitLab 新手入门
---

## 推荐学习路径

```
第 1 周：注册 + Git 工作流 + 项目/MR
  └─ 篇 1~5

第 2 周：CI/CD 基础 + Runner + Pipeline
  └─ 篇 6~9

第 3 周：Docker/Registry + Pages + 协作
  └─ 篇 10~15

第 4 周：K8s + Webhook + Review + 排查
  └─ 篇 16~19

第 5 周：Checklist 验收 + 综合实战
  └─ 篇 20
```

## 入门 Checklist

### 基础

- [ ] 账号注册，SSH Key 配置
- [ ] 创建 Group + Project
- [ ] 完成 clone → branch → push → MR 全流程
- [ ] main 保护分支已配置

### CI/CD

- [ ] `.gitlab-ci.yml` 至少 lint/build/test 三 stage
- [ ] Runner 注册且 Job 可 passed
- [ ] CI 变量存放密钥（Mask + Protect）
- [ ] Docker 镜像 push 到 Registry 成功

### 协作

- [ ] Issue + Label + Milestone 使用过
- [ ] MR 经过 Review 后合并
- [ ] Wiki 或 README 有项目说明

### 进阶

- [ ] Environment 记录 staging/prod 部署
- [ ] 与 K8s 或 GitOps 仓联动一次
- [ ] Webhook 或 Slack 通知配置

## 配套练习

| 练习 | 技能点 |
|------|--------|
| 静态站 push Pages | Pages + CI |
| Node 项目 CI 全套 | lint/test/build |
| MR 关闭 Issue | 协作联动 |
| 镜像部署 K8s | Registry + deploy |

## 推荐资源

- [GitLab 官方文档](https://docs.gitlab.com/)
- [GitLab CI YAML 参考](https://docs.gitlab.com/ee/ci/yaml/)
- [.gitlab-ci.yml 示例集合](https://gitlab.com/gitlab-org/gitlab/-/tree/master/lib/gitlab/ci/templates)

## 延伸（后续可学）

- **GitLab SRE 系列**（高可用、备份、安全）
- **ArgoCD 新手入门**（GitOps 部署）
- **Jenkins SRE**（与 GitLab CI 选型对比）

---

**GitLab 新手入门系列 20 篇**完结，从零到能独立搭建项目 CI/CD 与协作流程。建议配合 **Kubernetes**、**Docker** 基础一起实践。
