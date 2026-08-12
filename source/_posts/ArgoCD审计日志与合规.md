---
title: Argo CD 审计日志与合规
date: 2026-08-27 13:15:00
tags:
  - ArgoCD
  - SRE
  - 审计
categories:
  - ArgoCD SRE
---

金融、政企等场景要求 **谁、何时、对哪个应用做了什么** 可追溯。

## 审计日志启用

```yaml
# argocd-cm
audit.log.format: json
audit.log.maxage: "365"
audit.log.maxbackup: "10"
audit.log.maxsize: "100"
```

日志由 server 输出，需 **采集到 SIEM**（Loki/ELK/Splunk）。

## 审计事件类型

| 事件 | 示例 |
|------|------|
| sync | user sync production/my-app |
| rollback | rollback to revision 3 |
| login | SSO login success/fail |
| repo update | add repository |
| cluster update | cluster add/remove |
| policy change | rbac-cm 变更 |

## 日志样例

```json
{
  "level": "info",
  "msg": "sync initiated",
  "user": "sre@example.com",
  "application": "production/my-app",
  "time": "2026-08-27T10:00:00Z"
}
```

## 合规要求映射

| 要求 | 实现 |
|------|------|
| 变更可追溯 | Git commit + audit log |
| 职责分离 | RBAC prod sync 仅 SRE |
| 审批 | PR review + branch protection |
| 保留期 | audit ≥ 1 年 |

## syncWindow（变更窗口）

```yaml
# AppProject
syncWindows:
  - kind: deny
    schedule: "0 0 * * 0"
    duration: 24h
    applications:
      - production/*
  - kind: allow
    schedule: "0 9-18 * * 1-5"
    duration: 9h
    manualSync: true
```

## 反模式

- 无 audit 仅依赖 Git（Git 不知谁点了 Sync）
- audit 日志未集中、未告警异常 login
- prod 无 syncWindow 无 PR 流程

审计配置纳入 **SOC2/等保** 控制项清单。
