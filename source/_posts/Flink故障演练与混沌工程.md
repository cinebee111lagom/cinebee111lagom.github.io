---
title: Flink 故障演练与混沌工程
date: 2026-08-18 13:15:00
tags:
  - Flink
  - 混沌工程
categories:
  - Flink SRE
---

Flink 故障演练验证 JM HA、Checkpoint 恢复与 Runbook 有效性。

## 演练场景

| 场景 | 注入 | 预期 |
|------|------|------|
| JM 宕机 | kill active JM | Standby 接管，作业恢复 |
| TM OOM | 限内存 / kill TM | 重启 subtask，从 CK 恢复 |
| Checkpoint 失败 | 改错 S3 路径 | 告警，作业不 silently 丢数据 |
| 网络分区 | toxiproxy 阻断 Kafka | 反压/失败可观测 |
| Savepoint 升级 | 发版流程 | 状态连续、数据对账通过 |
| 全集群重启 | 滚动重启 TM | Checkpoint 恢复成功 |

## JM Failover 演练

```bash
# staging
kubectl delete pod -l component=jobmanager,role=active
# 观察恢复时间、records 连续性
```

## Savepoint 升级演练

```bash
flink stop --savepointPath s3://bucket/drill/$(date +%Y%m%d) <jobId>
flink run -s <path> -c com.example.Job job-new.jar
# 对账 15 分钟窗口数据
```

## 混沌工具

- **Chaos Mesh**：Pod kill、网络延迟、IO 压力
- **Litmus**：K8s 故障注入
- **手动**：iptables、S3 临时 deny

## Game Day

```
09:00  Briefing，冻结变更
09:30  TM kill + 恢复
11:00  Checkpoint 存储故障模拟
14:00  Savepoint 跨集群恢复
16:00  Postmortem + 改进项
```

## 成功标准

- [ ] RTO ≤ SLA
- [ ] 无未预期数据丢失（对账）
- [ ] 告警 5 分钟内触发
- [ ] Runbook 可独立执行
- [ ] 改进项录入 backlog

## 注意

- 仅在 staging / 可回滚窗口
- 生产演练需审批
- 保留 savepoint 快照

**未演练的 Savepoint 恢复等于不会恢复**。
