---
title: Kafka SRE 上线 Checklist 与生产 Runbook
date: 2026-08-16 13:45:00
tags:
  - Kafka
  - SRE
  - Runbook
categories:
  - Kafka SRE
---

## 上线 Checklist

### 架构

- [ ] 架构文档已评审（KRaft/ZK、Broker 数、跨 AZ）
- [ ] replication.factor=3，min.insync.replicas=2
- [ ] 容量压测：吞吐、磁盘、网络余量 ≥ 40%

### 配置

- [ ] 生产参数基线已应用
- [ ] log.dirs 独立 SSD
- [ ] Retention 与合规对齐
- [ ] 内部 Topic RF=3
- [ ] unclean.leader.election=false

### 安全

- [ ] SASL_SSL 全链路
- [ ] ACL 最小权限
- [ ] allow.everyone.if.no.acl.found=false
- [ ] 无公网裸端口

### 备份与容灾

- [ ] MM2 或等效跨集群复制（若需 DR）
- [ ] DR 切换演练 3 个月内完成
- [ ] Schema Registry / Connect RF=3

### 监控

- [ ] kafka_exporter / JMX + Prometheus
- [ ] Grafana Dashboard
- [ ] URP、Offline、Lag、磁盘 P0/P1 告警
- [ ] 告警带 Runbook 链接

---

## 日常 Runbook

### Offline Partitions（P0）

```bash
kafka-topics.sh --describe --under-replicated-partitions \
  --bootstrap-server localhost:9092
kafka-metadata-quorum.sh --bootstrap-server localhost:9092 describe --status
# 恢复 down Broker 或替换节点
```

### Broker 宕机

```bash
systemctl status kafka
tail -200 /var/log/kafka/server.log
df -h /data/kafka-logs
# 重启或替换，等待 ISR 同步
```

### Lag 飙升

```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group <group>
# 扩消费者、查下游、查 poison message
```

### 磁盘满

- 调低 Retention（临时）
- 删测试 Topic
- 扩容磁盘
- 禁止删 active segment

### 紧急扩容 Broker

1. 部署新 Broker 加入集群
2. `kafka-reassign-partitions` 均衡
3. 验证 URP=0
4. 更新监控

### Controller 异常

- KRaft：`kafka-metadata-quorum describe`
- 检查 quorum 连通与 JVM GC
- 滚动重启 Controller 节点

---

**Kafka SRE 系列 20 篇**完结，涵盖部署、HA、备份、监控、Lag、安全、K8s、Topic、Connect、磁盘、容灾与演练。建议配合 **Redis SRE**、**MySQL SRE**、**PostgreSQL SRE** 系列对照阅读，构建完整数据基础设施 SRE 知识体系。
