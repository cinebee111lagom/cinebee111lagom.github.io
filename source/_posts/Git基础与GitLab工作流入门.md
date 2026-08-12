---
title: Git 基础与 GitLab 工作流入门
date: 2026-08-28 09:30:00
tags:
  - GitLab
  - Git
  - 入门
categories:
  - GitLab 新手入门
---

GitLab 建立在 Git 之上，掌握 **clone → branch → commit → push → MR** 是第一步。

## 克隆仓库

```bash
# SSH（推荐）
git clone git@gitlab.com:mygroup/my-project.git

# HTTPS
git clone https://gitlab.com/mygroup/my-project.git
```

## 日常开发流程

```bash
cd my-project
git checkout -b feature/add-login
# 编辑代码...
git add .
git commit -m "feat: add login page"
git push -u origin feature/add-login
```

然后在 GitLab UI 创建 **Merge Request**。

## 标准工作流

```
main（保护分支）
  ↑ MR + Review
feature/*（功能分支）
hotfix/*（紧急修复）
```

## 常用 Git 命令

| 命令 | 作用 |
|------|------|
| git status | 查看变更 |
| git log --oneline | 提交历史 |
| git pull --rebase | 拉取并变基 |
| git fetch origin | 仅拉取不合并 |
| git merge origin/main | 合并主分支 |

## 与 GitLab 集成功能

| 操作 | GitLab 增强 |
|------|-------------|
| push | 触发 CI Pipeline |
| MR | Code Review、Approval |
| commit message | 关闭 Issue（`Closes #12`） |
| tag | 触发 release pipeline |

## .gitignore

项目根目录添加 `.gitignore`，避免提交 `node_modules/`、`.env` 等。

## 反模式

- 直接在 main 上 commit（无 Review）
-  giant commit 无意义 message
- 把 Secret 提交进 Git

下一篇：**项目创建与仓库管理**。
