---
title: GitLab 代码审查与 MR 最佳实践入门
date: 2026-08-28 13:15:00
tags:
  - GitLab
  - Code Review
  - 入门
categories:
  - GitLab 新手入门
---

高质量 **Code Review** 提升代码质量，GitLab MR 提供完整审查工具。

## Review 工作流

```
Author 开 MR → 指定 Reviewer → CI 通过
  → Reviewer 评论 → Author 修改 push
  → Approve → Maintainer Merge
```

## MR 大小建议

| 规模 | 行数 | 建议 |
|------|------|------|
| 小 | < 200 | 理想 |
| 中 | 200~400 | 可接受 |
| 大 | > 500 | 拆分 |

## 评论类型

- **General comment**：整体讨论
- **Inline comment**：针对具体行
- **Suggestion**：可直接 Apply 的修改建议

## Draft MR

```
Create merge request → Mark as draft
```

WIP 期间不通知 Reviewer，完成后 **Mark ready**。

## CODEOWNERS（可选）

```
# CODEOWNERS
*.go @backend-team
/docs/ @tech-writers
```

对应文件变更自动请求 Owner Review。

## CI 与 Review 门禁

**Settings → Merge requests**

- [ ] Pipelines must succeed
- [ ] All threads must be resolved
- [ ] Approval rules（EE）

## Commit 规范

```
feat(auth): add JWT login
fix(api): handle null user id
docs: update README deploy section
```

配合 **Squash merge** 保持 main 历史整洁。

## 反模式

- LGTM 无细看
- Reviewer 自己改作者分支无沟通
- 红 CI 仍 Merge

下一篇：**常见问题与排查**。
