---
title: Kafka 监控体系：Prometheus 与 kafka_exporter
date: 2026-08-16 10:30:00
tags:
  - Kafka
  - Prometheus
  - 监控
categories:
  - Kafka SRE
---

Kafka 监控以 JMX + kafka_exporter + Prometheus + Grafana 为主流方案。

## kafka_exporter 部署

```bash
./kafka_exporter --kafka.server=10.0.1.11:9092 \
  --kafka.server=10.0.1.12:9092 \
  --web.listen-address=:9308
```

或使用 **Burrow**（LinkedIn）专精 Consumer Lag。

## 核心 Broker 指标

| 指标 | 含义 | 告警 |
|------|------|------|
| `kafka_server_replicamanager_underreplicatedpartitions` | URP | > 0 持续 P1 |
| `kafka_controller_kafkacontroller_offlinepartitionscount` | 离线分区 | > 0 P0 |
| `kafka_network_requestmetrics_totaltimems` | 请求延迟 | P99 突增 |
| `kafka_log_log_size` | 日志大小 | 磁盘 80% |
| `kafka_server_brokertopicmetrics_messagesin_total` | 入站消息 | 突降 50% |

## Consumer Lag

```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group my-app-group
```

Prometheus：`kafka_consumergroup_lag`（kafka_exporter 或 Burrow）。

## JMX Exporter（补充）

```yaml
# jmx_exporter config
rules:
  - pattern: kafka.server<type=BrokerTopicMetrics, name=MessagesInPerSec><>OneMinuteRate
    name: kafka_broker_messages_in_per_sec
```

## Grafana Dashboard

- **7589** — Kafka Overview
- **721** — Kafka Consumer Lag
- Confluent 官方 Dashboard

## 日志

```properties
log4j.logger.kafka.request.logger=WARN
log4j.logger.kafka.controller=INFO
```

→ ELK/Loki，关联 trace_id（若 header 传递）。

## 检查清单

- [ ] 每 Broker 有 exporter
- [ ] URP、Offline、Lag P0/P1 告警
- [ ] 磁盘、网络带宽监控
- [ ] Controller 选举事件告警
- [ ] 告警带 Runbook 链接

可观测三件套：**Broker 健康、Lag、磁盘**。
