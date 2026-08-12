---
title: GitLab 故障演练与混沌工程
date: 2026-08-29 13:00:00
tags:
  - GitLab
  - SRE
  - 混沌工程
categories:
  - GitLab SRE
---

GitLab 控制面故障阻断 **全公司开发**，演练验证 HA 与 Runbook。

## 演练场景（staging）

| 场景 | 操作 | 期望 |
|------|------|------|
| App 节点宕机 | stop puma | LB 切另一节点 |
| Sidekiq 停 | stop sidekiq | 队列积压告警 |
| Gitaly 节点挂 | stop gitaly | Cluster 仍可用 |
| PG failover | patroni switchover | <2min 恢复 |
| Redis 主切换 | sentinel failover | 短暂抖动 |
| Runner 全 offline | stop runners | P1 + 队列等待 |

## 业务演练

```
1. 模拟 Primary 不可用
2. 从 backup restore 到隔离环境（测 RTO）
3. Geo promote（若有）
4. 验证 git push、MR merge、Pipeline
```

## 成功标准

- P0 告警触达 on-call
- RTO 符合 SLA
- 无未文档化手工步骤
- 用户通知模板可用

## 安全注意

- **禁止**未通知对 prod 混沌
- 演练窗口 + 回滚预案
- 备份先于破坏性操作

## 频率

| 演练 | 周期 |
|------|------|
| 单组件故障 | 月（staging） |
| Backup restore | 季 |
| Geo failover | 半年 |

## 反模式

- HA 装完从未 failover
- 演练不更新 Runbook
- 只测 health 不测 git push

演练报告进 **SRE 季度复盘**。
