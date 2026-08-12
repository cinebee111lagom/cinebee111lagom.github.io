---
title: Jenkins 故障演练与混沌工程
date: 2026-08-23 13:15:00
tags:
  - Jenkins
  - 混沌工程
categories:
  - Jenkins SRE
---

故障演练验证 Jenkins HA、备份恢复与 Runbook 有效性。

## 演练场景

| 场景 | 注入 | 预期 |
|------|------|------|
| Controller 宕机 | stop 服务 | HA failover ≤ RTO |
| NFS 不可用 | 卸载 volume | 告警，禁止 split-brain |
| 全部 Agent 离线 | 停 agent 服务 | 队列告警，无误构建 |
| 磁盘满 | 填满 JENKINS_HOME | 只读/失败可观测 |
| 插件故障 | 错误插件版本 | 安全模式恢复 |
| 备份恢复 | 删 Job 后 restore | 数据完整 |

## Controller Failover 演练

```
1. 记录当前 Job 与 queue
2. stop Controller-1
3. LB 切 Controller-2
4. 触发 smoke Pipeline
5. 记录 RTO
6. 恢复 Controller-1 为 standby
```

## 备份 Restore 演练

```
1. 创建测试 Job 并构建
2. 执行备份
3. 全新 Controller 从备份 restore
4. 验证 Job 历史与凭据可用
5. 跑 test Pipeline
```

## 构建失败 vs 平台故障

演练区分：
- 故意改坏 Jenkinsfile → 应 Job 失败，平台健康
- 停 Agent → 平台 P1 告警

## Game Day

```
09:00  Briefing
09:30  Controller failover
11:00  Backup restore
14:00  Agent 池全离线恢复
16:00  Postmortem
```

## 成功标准

- [ ] RTO ≤ SLA
- [ ] 告警 5 分钟内触发
- [ ] Runbook 可执行无歧义
- [ ] 无凭据丢失
- [ ] 改进项 backlog

**未演练的 HA 和备份不可信**。
