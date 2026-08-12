---
title: PostgreSQL 故障演练与混沌工程
date: 2026-08-15 13:30:00
tags:
  - PostgreSQL
  - 混沌工程
  - SRE
categories:
  - PostgreSQL SRE
---

故障演练验证 HA、备份、监控与 Runbook 在真实故障下是否有效。

## 演练原则

- **staging 先行**，生产低峰 + 变更窗口
- 可观测：全程录屏指标与日志
- 可回滚：备份就绪、On-Call 待命
- 事后 Postmortem

## 演练场景清单

| 场景 | 注入方式 | 预期 |
|------|----------|------|
| Primary 宕机 | `systemctl stop postgresql` / kill -9 | Patroni 30s 内 failover |
| 网络分区 | iptables 阻断 5432 | 无脑裂，告警触发 |
| 复制中断 | 停 standby | 告警，主库正常写 |
| 磁盘满 | dd 填满挂载 | 告警，服务降级可预期 |
| WAL 归档失败 | 改错 archive_command | 告警，主库不删 WAL |
| PgBouncer 重启 | systemctl restart | 应用重连 < 30s |
| 慢查询风暴 | pg_sleep 压测 | auto_explain + 限流 |

## Patroni Failover 演练

```bash
# staging
patronictl switchover pg-cluster --master pg1 --candidate pg2
# 验证
psql -h haproxy-write -c "SELECT pg_is_in_recovery();"
```

记录：切换耗时、应用错误率、复制重建时间。

## PITR 演练

1. 创建测试表写入数据
2. 记录时间 T1，误删数据
3. 从备份 + WAL 恢复到 T1
4. 验证数据完整

## 混沌工具

- **Chaos Mesh / Litmus**：K8s pod kill、网络延迟
- **toxiproxy**：注入网络故障
- **自定义脚本**：cron 随机 kill 连接

## 游戏日（Game Day）流程

```
09:00  Briefing + 冻结无关变更
09:30  场景 1：Primary fail
10:30  场景 2：Region 网络分区
12:00  午餐复盘
14:00  场景 3：PITR 恢复
16:00  Postmortem 文档
```

## 成功标准

- [ ] RTO 实测 ≤ SLA
- [ ] 告警 5 分钟内触达 On-Call
- [ ] Runbook 步骤完整无歧义
- [ ] 无未预期数据丢失
- [ ] 改进项录入 backlog

**未演练的 HA 等于没有 HA**。
