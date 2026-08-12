---
title: GitLab 分支策略与 Merge Request 入门
date: 2026-08-28 10:00:00
tags:
  - GitLab
  - Merge Request
  - 入门
categories:
  - GitLab 新手入门
---

**Merge Request（MR）** 是 GitLab 代码审查与合并的核心机制。

## 常见分支模型

| 模型 | 分支 | 适用 |
|------|------|------|
| Git Flow | main + develop + feature | 版本发布型 |
| GitHub Flow | main + feature | 持续部署 |
| Trunk Based | main + 短 feature | 高频集成 |

新手推荐：**main + feature/**，简单清晰。

## 创建 MR

1. push feature 分支
2. GitLab 提示 **Create merge request**
3. 填写 Title、Description、Reviewer
4. 等待 CI 通过 + Review 批准
5. **Merge**

## MR 描述模板

```markdown
## 变更说明
- 添加用户登录 API

## 测试
- [ ] 单元测试通过
- [ ] 本地手动验证

## 关联 Issue
Closes #42
```

Settings → Merge requests → **Template** 可设默认模板。

## 保护分支规则

**Settings → Repository → Protected branches**

| 分支 | Allowed to merge | Allowed to push |
|------|------------------|-----------------|
| main | Maintainers + MR | No one |

## Approval Rules（EE/部分 CE）

- 至少 1 人 Approve
- Code Owner 必须 Review

## 解决冲突

```bash
git checkout feature/add-login
git fetch origin
git rebase origin/main
# 解决冲突
git push -f origin feature/add-login
```

## 反模式

- MR 过大（> 500 行）难 Review
- CI 红仍 Merge
- 无 Description 的 MR

下一篇：**GitLab CI/CD 核心概念**。
