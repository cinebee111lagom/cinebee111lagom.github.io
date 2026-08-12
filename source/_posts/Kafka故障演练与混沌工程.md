---
title: Kafka 故障演练与混沌工程
date: 2026-08-16 13:15:00
tags:
  - Kafka
  - 混沌工程
  - SRE
categories:
  - Kafka SRE
---

故障演练验证 Kafka HA、监控告警与 Runbook 在真实故障下是否有效。

## 演练原则

- staging 先行，生产低峰 + 变更窗口
- 全程记录指标与日志
- On-Call 待命，可快速回滚
- 48h 内 Postmortem

## 演练场景

| 场景 | 注入方式 | 预期 |
|------|----------|------|
| 单 Broker 宕机 | kill -9 / stop | Leader 切换，URP 短暂后恢复 |
| 整 AZ 不可用 | 停 AZ 内全部 Broker | 分区仍可用（RF=3 跨 AZ） |
| 磁盘满 | dd 填满 | 告警，Broker 拒写 |
| 网络分区 | iptables 阻断 9092 | Controller 行为符合预期 |
| Consumer 全挂 | 停所有 consumer | Lag 告警，Broker 正常 |
| MM2 中断 | 停 Connect | DR lag 告警 |
| ZK/KRaft 节点故障 | 停 1 节点 | quorum 仍健康 |

## Broker Failover 演练

```bash
# staging
systemctl stop kafka   # Broker2
sleep 30
kafka-topics.sh --describe --topic orders --bootstrap-server remaining:9092
# 验证 Leader 迁移、生产消费正常
systemctl start kafka
# 验证 ISR 重建
```

## DR 切换演练

1. 记录 Primary offset
2. 停 Primary 模拟故障
3. 客户端切 DR bootstrap
4. 验证消费连续性
5. 恢复 Primary + MM2

## 混沌工具

- **Chaos Mesh**：K8s pod kill、网络延迟
- **toxiproxy**：Broker 间延迟注入
- **kafka-producer-perf-test**：压测期间注入故障

## Game Day 流程

```
09:00  Briefing
09:30  场景 1：Broker 宕机
10:30  场景 2：磁盘满
14:00  场景 3：DR 切换
16:00  Postmortem
```

## 成功标准

- [ ] RTO 实测 ≤ SLA
- [ ] Offline Partition = 0（或可接受窗口内恢复）
- [ ] 告警 5 分钟内触达
- [ ] Runbook 步骤无歧义
- [ ] 改进项录入 backlog

**未演练的 RF=3 不等于高可用**。
