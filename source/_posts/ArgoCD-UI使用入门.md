---
title: Argo CD UI 使用入门
date: 2026-08-26 12:45:00
tags:
  - ArgoCD
  - UI
  - 入门
categories:
  - ArgoCD 新手入门
---

UI 是值班与开发排查的直观入口，与 CLI 能力互补。

## 主界面概览

| 区域 | 内容 |
|------|------|
| Applications | 所有应用卡片/列表 |
| Settings | 仓库、集群、项目、凭证 |
| User Info | 当前用户与权限 |

应用卡片显示：**Sync 状态**、**Health**、**最后同步时间**。

## Application 详情页

```
┌─────────────────────────────────────┐
│  APP DETAILS  │  SYNC  │  HISTORY   │
├─────────────────────────────────────┤
│         资源拓扑树（Pod/Deploy/Svc）   │
│    绿色=Healthy  黄色=Progressing    │
└─────────────────────────────────────┘
```

### 常用操作

| 按钮 | 作用 |
|------|------|
| Sync | 同步 Git → 集群 |
| Refresh | 重新对比 Git（不 deploy） |
| Diff | 查看 Live vs Desired |
| History | 历史 Sync 与 Rollback |
| Delete | 删除 Application（可选 cascade） |

## Sync 对话框选项

- **Prune**：删除 Git 中不存在的资源
- **Dry Run**：预览不执行
- **Apply Only Out of Sync**：仅 apply 差异
- **Force**：跳过 hook 冲突（谨慎）

## 资源级操作

点击 Pod → **Logs** 看容器日志（需 RBAC 权限）。

部分资源支持 **Delete** 单个资源（不推荐替代 Git 管理）。

## 过滤与搜索

```
Labels: env=prod
Projects: team-backend
Sync Status: OutOfSync
```

## 终端 vs UI

| 场景 | 推荐 |
|------|------|
| 快速看健康 | UI |
| 批量 sync | CLI |
| CI 自动化 | CLI |
| 新人 onboarding | UI |
| Diff 细节 | UI Diff 视图更直观 |

## 自定义 UI

- **ApplicationSet** 批量创建应用后 UI 自动出现
- **Links**：argocd-cm 配置外部链接（Grafana、日志）

## 反模式

- 生产变更只点 UI 不改 Git
- 多人同时 Force Sync
- 不 Refresh 就看 Diff（可能缓存旧）

UI 熟练后，结合 CLI 可覆盖日常 GitOps 全流程。
