---
title: GitLab 权限与成员角色入门
date: 2026-08-28 12:15:00
tags:
  - GitLab
  - 权限
  - 入门
categories:
  - GitLab 新手入门
---

GitLab 用 **Role** 控制成员能做什么，遵循最小权限原则。

## 项目级角色（低→高）

| 角色 | 典型权限 |
|------|----------|
| Guest | 看 Issue/Wiki |
| Reporter | 看代码、下载 |
| Developer | push 非保护分支、跑 CI |
| Maintainer | 改设置、合并保护分支 |
| Owner | Group 级完全控制 |

## 邀请成员

**Project → Manage → Members → Invite**

可邀请个人或 **Group 继承**。

## Group 继承

```
Team Group（Developer 角色）
  └── 子 Project 自动继承 Developer
```

在 Group 加人，子项目自动获得权限。

## 保护分支与角色

```
main 分支：
  Merge：Maintainer
  Push：No one
```

Developer 只能走 MR，不能直接 push main。

## CI/CD 权限

| 操作 | 最低角色 |
|------|----------|
| 查看 Pipeline | Reporter |
| 运行 Job | Developer |
| 改 CI 变量 | Maintainer |
| 注册 Runner | Maintainer |

## Project Access Token

**Settings → Access Tokens**

用于 CI、Bot、外部集成，比个人 PAT 更安全。

## 反模式

- 全员 Maintainer
- 离职人员未移除
- Bot 使用个人账号 Token

下一篇：**Container Registry**。
