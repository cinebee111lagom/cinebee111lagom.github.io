---
title: Kafka SRE 告警规则与值班手册
date: 2026-08-16 10:45:00
tags:
  - Kafka
  - SRE
  - 告警
categories:
  - Kafka SRE
---

Kafka 告警需区分 Broker 级、Topic 级与 Consumer 级，避免 Lag 噪音。

## 告警分级

| 级别 | 场景 | 响应 |
|------|------|------|
| P0 | Offline Partitions、集群不可写 | 5 分钟 |
| P1 | URP 持续、Broker down、Lag > 阈值 | 15 分钟 |
| P2 | 磁盘 >75%、请求延迟升高 | 1 小时 |
| P3 | 证书过期、非核心 Topic Lag | 下一工作日 |

## Prometheus 规则示例

```yaml
groups:
  - name: kafka
    rules:
      - alert: KafkaOfflinePartitions
        expr: kafka_controller_kafkacontroller_offlinepartitionscount > 0
        for: 1m
        labels:
          severity: critical

      - alert: KafkaUnderReplicatedPartitions
        expr: kafka_server_replicamanager_underreplicatedpartitions > 0
        for: 5m
        labels:
          severity: warning

      - alert: KafkaConsumerLagHigh
        expr: kafka_consumergroup_lag > 100000
        for: 10m
        labels:
          severity: warning

      - alert: KafkaBrokerDown
        expr: up{job="kafka_exporter"} == 0
        for: 2m
        labels:
          severity: critical
```

## 值班速查

### Broker 不可达

```bash
systemctl status kafka
tail -200 /var/log/kafka/server.log
df -h /data/kafka-logs
jcmd <pid> VM.flags   # JVM 检查
```

### URP 排查

```bash
kafka-topics.sh --describe --under-replicated-partitions \
  --bootstrap-server localhost:9092
# 检查 Follower Broker 是否 down、网络、磁盘满
```

### Lag 飙升

```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group my-group
# 消费慢？分区不均？下游故障？
```

### 磁盘满

- 检查 Retention 是否过长
- 清理临时 Topic
- 扩容磁盘或启用 Tiered Storage
- **禁止** 手动删 `log.dirs` 内 active segment

### Controller 频繁切换

- 检查 Controller 节点 GC、网络
- KRaft 检查 quorum 连通性

## On-Call 原则

1. Offline Partition 最高优先级
2. 扩容分区不能降 Lag（需扩消费者）
3. 变更前确认 ISR 健康
4. 事故 48h 内 Postmortem

每季度 review 告警阈值，**Lag 按 Consumer Group 分级**。
