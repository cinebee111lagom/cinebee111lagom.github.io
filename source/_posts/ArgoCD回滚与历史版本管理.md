---
title: Argo CD 回滚与历史版本管理
date: 2026-08-26 12:00:00
tags:
  - ArgoCD
  - 回滚
  - 入门
categories:
  - ArgoCD 新手入门
---

GitOps 回滚有两种路径：**Git revert**（推荐）与 **Argo CD History Rollback**（应急）。

## 方式一：Git Revert（推荐）

```bash
# 找到问题 commit
git log apps/myapp/overlays/prod/kustomization.yaml

# revert 并 push
git revert <bad-commit>
# Argo CD 检测 OutOfSync → Sync → 回到上一版本
```

**优点**：Git 即审计记录，与 GitOps 理念一致。

## 方式二：Argo CD History Rollback

每次 Sync 会记录 deployment history：

```bash
argocd app history my-app

ID  DATE                           REVISION
0   2026-08-26 10:00:00 +0800      abc123 (main)
1   2026-08-26 11:00:00 +0800      def456 (main)

argocd app rollback my-app 0
```

UI：Application → History → Rollback。

**注意**：Rollback 只回滚集群，**Git 仍是最新** → 会再次 OutOfSync。应急后应 **Git revert 对齐**。

## 镜像 tag 回滚示例

```yaml
# kustomization.yaml prod overlay
images:
  - name: registry.io/myapp
    newTag: v1.1.0   # 从 v1.2.0 改回
```

```bash
git commit -m "rollback: myapp to v1.1.0"
git push
argocd app sync my-app
```

## 与 Deployment rollout undo 对比

| | kubectl rollout undo | GitOps revert |
|---|---------------------|---------------|
| 变更记录 | 无 Git 记录 | Git 有 PR |
| 漂移 | 造成 OutOfSync | 保持一致 |
| selfHeal | 可能被改回 | 正确状态 |

**禁止**生产 `kubectl rollout undo` 而不改 Git（若开 selfHeal）。

## 发布记录

结合 Git tag 标记每次 prod 发布：

```bash
git tag -a myapp-v1.2.0 -m "prod release"
git push origin myapp-v1.2.0
```

Application 可 pin `targetRevision: myapp-v1.2.0`。

## 反模式

- 只 rollback 不改 Git，selfHeal 下混乱
- 无 history 保留（默认有）
- prod 无 tag 无法快速 pin 已知好版本

下一篇：**Secret 管理**入门。
