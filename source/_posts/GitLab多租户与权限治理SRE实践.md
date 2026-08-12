---
title: GitLab 多租户与权限治理 SRE 实践
date: 2026-08-29 12:30:00
tags:
  - GitLab
  - SRE
  - 权限
categories:
  - GitLab SRE
---

大型组织用 **Group 层级 + 最小权限** 治理多租户。

## Group 结构

```
org（Owner: IT）
├── platform（Maintainer: SRE）
├── team-a
│   ├── service-x（Developer: Team A）
│   └── service-y
└── team-b
```

## 权限原则

| 原则 | 实现 |
|------|------|
| 默认最小 | 新成员 Guest/Reporter |
| 继承可控 | 子 Group 降低权限可 break inheritance |
| 共享 Runner | Group 级，Project 不可改 |
| prod 环境 | Maintainer+ 才能 deploy |

## Protected branches

```
main / release/*:
  merge: Maintainers
  push: No one
  code owners approval（EE）
```

## CI Variables 作用域

| 级别 | 用途 |
|------|------|
| Instance | 全局 registry |
| Group | 团队密钥 |
| Project | 项目专用 |
| Protected | 仅保护分支 Pipeline |

## 定期审计

```bash
# API 导出成员与权限
GET /groups/:id/members
GET /projects/:id/protected_branches
```

季度：**孤儿项目、过期 Token、Owner 过多** 清理。

## 反模式

- 所有人 org Owner
- 公开项目误开
- Group Variable 不 Protected 被 fork MR 读取

权限变更 **工单 + Audit log** 双轨。
