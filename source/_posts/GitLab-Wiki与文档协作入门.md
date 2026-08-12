---
title: GitLab Wiki 与文档协作入门
date: 2026-08-28 12:00:00
tags:
  - GitLab
  - Wiki
  - 入门
categories:
  - GitLab 新手入门
---

项目 **Wiki** 适合轻量文档；大文档建议独立仓 + Pages。

## Wiki 入口

**Plan → Wiki** → Create first page

支持 **Markdown**，可互相链接：

```markdown
[[Home]] [[API 设计]] [[部署说明]]
```

## 与 README 分工

| | README | Wiki |
|---|--------|------|
| 位置 | 仓库根目录 | GitLab 独立 Git 仓 |
| 版本 | 随代码 MR | Wiki 独立提交 |
| 适用 | 快速上手 | 长篇文档、Runbook |

## Clone Wiki（本地编辑）

```bash
git clone git@gitlab.com:mygroup/my-project.wiki.git
cd my-project.wiki
# 编辑 Home.md
git add . && git commit -m "update deploy doc" && git push
```

## Snippet 代码片段

**Snippets** 共享单文件代码/脚本，可 Secret（私有）。

## 文档最佳实践

```
Wiki Home
├── 架构概览
├── 开发环境搭建
├── API 说明（或链接 OpenAPI）
├── 部署 Runbook
└── 故障 FAQ
```

## 与 Issue 链接

Wiki 中引用 Issue：`#123`

## 反模式

- 所有文档堆 README 难维护
- Wiki 无结构首页
- 部署步骤只在口头不传 Wiki

大团队可 **Wiki + Pages 文档站** 组合使用。
