---
title: GitLab 常见问题与排查
date: 2026-08-28 13:30:00
tags:
  - GitLab
  - 排查
  - 入门
categories:
  - GitLab 新手入门
---

GitLab 新手高频问题与 **第一步排查**。

## Pipeline 一直 pending

| 原因 | 解决 |
|------|------|
| 无可用 Runner | 注册 Runner / 检查 tags |
| Runner offline | `gitlab-runner verify` |
| tags 不匹配 | Job tags 与 Runner 一致 |

```bash
sudo gitlab-runner list
sudo gitlab-runner verify
```

## Job 失败：script 错误

**Job 日志** → 看最后一行非零 exit code。

```yaml
# 调试
script:
  - set -x   # 打印命令
  - your-command
```

## Docker dind 失败

```
Cannot connect to Docker daemon
```

Runner `config.toml` 需 `privileged = true`（docker executor）。

## Registry 401

- Token 权限含 `read_registry` / `write_registry`
- CI 用 `$CI_REGISTRY_USER` 而非个人用户名

## MR 无法合并

| 原因 | 解决 |
|------|------|
| 冲突 | 本地 rebase main |
| CI 失败 | 修 Job |
| 缺 Approval | 找 Reviewer |
| 保护分支 | 需 Maintainer merge |

## SSH clone 失败

```bash
ssh -T git@gitlab.com
# Permission denied → 检查 SSH Key 是否添加
```

## 自建 GitLab 502

```bash
gitlab-ctl status
gitlab-ctl tail
# 常见：内存不足、磁盘满
```

## YAML 校验

**CI/CD → Editor → Validate**

或使用 [CI Lint API](https://docs.gitlab.com/ee/api/lint.html)。

## 排查流程

```
Pipeline pending → Runner
Job failed → 日志 + 本地复现
MR  blocked → CI / 冲突 / 权限
Registry → Token / login
```

收藏本文作 **GitLab 值班速查**。
