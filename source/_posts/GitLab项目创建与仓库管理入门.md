---
title: GitLab 项目创建与仓库管理入门
date: 2026-08-28 09:45:00
tags:
  - GitLab
  - 项目
  - 入门
categories:
  - GitLab 新手入门
---

**Project** 是 GitLab 的核心单元，对应一个 Git 仓库及配套 CI/Issue 等。

## 创建项目

**UI**：New project → Create blank project

| 选项 | 建议 |
|------|------|
| Project name | 小写连字符 `my-api` |
| Visibility | Private（默认） |
| Initialize | 可勾选 README |
| CI/CD | 可勾选 `.gitlab-ci.yml` 模板 |

## Group 组织

```
company（Group）
├── backend（Subgroup）
│   ├── user-service
│   └── order-service
└── frontend
    └── web-app
```

Group 便于 **统一权限、Runner、变量**。

## 仓库设置要点

**Settings → General**

- 默认分支：`main`
- 合并方法：Merge commit / Squash / Fast-forward
- 删除源分支：MR 合并后自动删除（推荐开启）

**Settings → Repository**

- 保护分支：`main` 禁止直接 push
- Deploy tokens：只读/读写部署凭证
- Mirror：与 GitHub 等双向/单向同步

## 导入现有仓库

```
New project → Import project → GitHub / 裸 Git URL
```

## README 模板

```markdown
# My API

## 开发
git clone ...
npm install && npm run dev

## CI
见 .gitlab-ci.yml
```

## 反模式

- 每人一个 Group 无组织结构
- Public 项目误提交密钥
- 不设保护分支

下一篇：**分支策略与 Merge Request**。
