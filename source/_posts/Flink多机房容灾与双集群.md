---
title: Flink 多机房容灾与双集群
date: 2026-08-18 13:00:00
tags:
  - Flink
  - 容灾
categories:
  - Flink SRE
---

Flink 无内置跨 Region 复制，容灾靠 **双集群 + Savepoint/Kafka 双消费** 架构。

## 拓扑

```
Region A: Flink 集群 A → 写 Kafka-A / DB-A（主）
Region B: Flink 集群 B → 写 Kafka-B / DB-B（备）
         MirrorMaker 2 同步 Kafka（可选）
```

## 主备模式

```
常态：仅集群 A 运行作业
故障：从最近 Savepoint 在集群 B 启动
前提：Checkpoint/Savepoint 存跨区域 S3（CRR）
```

```bash
# Region B 恢复
flink run -s s3://global-bucket/flink/savepoints/latest \
  -c com.example.Job job.jar
# bootstrap 改为 Region B 的 Kafka
```

## 双跑模式（高 SLA）

```
两集群同逻辑、不同 consumer group
下游按 msgId 去重
成本高，RTO ≈ 0
```

## Savepoint 异地

```yaml
state.savepoints.dir: s3://bucket-with-crr/flink/savepoints
```

S3 Cross-Region Replication 或定期 sync savepoint 到 DR 桶。

## Kafka 联动

- Primary Kafka → MM2 → DR Kafka
- Flink DR 作业读 DR Kafka，避免跨 Region 拉流

## 切换 Runbook

1. 确认 Region A 不可用
2. 取最新 Savepoint（S3 DR 副本）
3. Region B 修改连接串启动作业
4. 验证输出与监控
5. Region A 恢复后反向同步或降级为备

## RPO/RTO

| 方案 | RPO | RTO |
|------|-----|-----|
| Savepoint 周期备份 | Checkpoint 间隔 | 10~30min 启动作业 |
| 双跑 | ≈0 | 分钟级切流 |
| 冷备（仅 jar+配置） | 丢状态 | 小时级 |

## 检查清单

- [ ] Savepoint 跨 Region 可达
- [ ] DR 集群季度演练
- [ ] Kafka MM2 lag 监控
- [ ] 连接串配置化（ConfigMap）
- [ ] 切换对账流程

Flink 容灾**依赖 Savepoint + 外部系统**，需与 Kafka SRE 协同。
