---
title: GitLab Issue 与看板项目管理入门
date: 2026-08-28 11:45:00
tags:
  - GitLab
  - Issue
  - 入门
categories:
  - GitLab 新手入门
---

GitLab **Issue** 跟踪任务、缺陷、需求，可与 MR、CI 联动。

## 创建 Issue

**Issues → New issue**

| 字段 | 用途 |
|------|------|
| Title | 简短描述 |
| Description | Markdown 详情 |
| Assignee | 负责人 |
| Milestone | 版本/迭代 |
| Labels | 分类标签 |

## 常用 Label 体系

```
type::bug
type::feature
priority::high
status::in-progress
```

Group 级 **Label 管理** 可统一规范。

## 看板（Issue Board）

**Plan → Issue board**

```
Open → In Progress → Review → Done
（列对应 Label 或 Assignee）
```

敏捷团队常用作 **轻量 Kanban**。

## 与 MR 关联

```markdown
# MR 描述中
Closes #12
Fixes #15
Related to #20
```

合并 MR 后 Issue 自动关闭。

## Milestone 进度

```
v1.0.0 Milestone
├── Issue #1 ✅
├── Issue #2 🔄
└── Issue #3 ⬜
```

**Plan → Milestones** 查看 burn-down。

## 模板

**Settings → General → Issue templates**

```markdown
## 复现步骤
1.

## 期望行为

## 环境
```

## 反模式

- Issue 与 MR 无关联，追溯难
- Label 过多无规范
- 长期 open 的 Issue 不清理

下一篇：**Wiki 与文档协作**。
