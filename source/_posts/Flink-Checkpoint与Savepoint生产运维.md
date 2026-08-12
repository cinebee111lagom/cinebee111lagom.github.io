---
title: Flink Checkpoint 与 Savepoint 生产运维
date: 2026-08-18 10:15:00
tags:
  - Flink
  - Checkpoint
  - Savepoint
categories:
  - Flink SRE
---

Checkpoint 是运行时容错，Savepoint 是有计划变更的「人工快照」，SRE 需分别运维。

## Checkpoint 运维

```bash
# Web UI: Jobs → Checkpoints
# REST API
curl http://jm:8081/jobs/<jobId>/checkpoints

# 触发手动 savepoint（不停作业）
flink savepoint <jobId> s3://bucket/flink/savepoints/manual-$(date +%Y%m%d)
```

## Savepoint 用途

| 场景 | 操作 |
|------|------|
| 代码升级 | stop-with-savepoint → 新 jar 从 savepoint 启 |
| 扩缩并行度 | rescale savepoint |
| 迁移集群 | savepoint → 新集群 restore |
| 紧急回滚 | 保留最近 N 个 savepoint |

## 停止与升级流程

```bash
# 1. 触发 savepoint 并停止
flink stop --savepointPath s3://bucket/flink/savepoints/upgrade-v2 <jobId>

# 2. 从新 savepoint 启动
flink run -s s3://bucket/flink/savepoints/upgrade-v2/savepoint-xxx \
  -c com.example.OrdersJob orders-job-v2.jar

# K8s Operator
kubectl patch flinkdeployment orders-job --type=merge -p '
  spec:
    job:
      savepointTriggerNonce: 1
      upgradeMode: savepoint
'
```

## 保留策略

```yaml
execution.checkpointing.externalized-checkpoint-retention: RETAIN_ON_CANCELLATION
state.checkpoints.num-retained: 3
```

S3 生命周期规则清理过期 Checkpoint（保留 7~14 天）。

## 对齐与超时

| 问题 | 调参 |
|------|------|
| 对齐慢 | 缓冲 debloat、增 timeout |
| 状态大 | 增量 Checkpoint、RocksDB |
| 频繁失败 | 查 TM 日志、S3 限流 |

## 检查清单

- [ ] Checkpoint 成功率 > 99%
- [ ] 平均耗时 < SLA
- [ ] Savepoint 路径独立、有版本命名
- [ ] 升级前必做 savepoint
- [ ] 定期验证 savepoint 可 restore

**Savepoint 是变更的安全气囊**，重大发布无 savepoint 不上线。
