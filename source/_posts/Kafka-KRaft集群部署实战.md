---
title: Kafka KRaft 集群部署实战
date: 2026-08-16 09:30:00
tags:
  - Kafka
  - KRaft
  - 部署
categories:
  - Kafka SRE
---

KRaft（Kafka Raft）模式用内置 Raft 元数据管理替代 ZooKeeper，是 Kafka 3.3+ 推荐部署方式。

## 节点规划

| 角色 | 数量 | 说明 |
|------|------|------|
| Broker + Controller | 3 或 5 | 小集群可合并 |
| 纯 Broker | N | 扩容时加 |
| 纯 Controller | 3 | 大集群分离（可选） |

## 生成 Cluster ID

```bash
KAFKA_CLUSTER_ID=$(bin/kafka-storage.sh random-uuid)
echo $KAFKA_CLUSTER_ID
```

## 格式化存储

```bash
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties
```

## server.properties 关键配置

```properties
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@10.0.1.11:9093,2@10.0.1.12:9093,3@10.0.1.13:9093
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
advertised.listeners=PLAINTEXT://10.0.1.11:9092
log.dirs=/data/kafka-logs
num.partitions=6
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
```

## 启动与验证

```bash
bin/kafka-server-start.sh -daemon config/kraft/server.properties

bin/kafka-broker-api-versions.sh --bootstrap-server 10.0.1.11:9092
bin/kafka-metadata-quorum.sh --bootstrap-server 10.0.1.11:9092 describe --status
```

## 创建测试 Topic

```bash
bin/kafka-topics.sh --create --topic test \
  --bootstrap-server 10.0.1.11:9092 \
  --partitions 6 --replication-factor 3

bin/kafka-topics.sh --describe --topic test --bootstrap-server 10.0.1.11:9092
```

## 部署检查清单

- [ ] Controller 节点奇数（3/5）
- [ ] `log.dirs` 独立磁盘，非系统盘
- [ ] `advertised.listeners` 可被客户端/其他 Broker 访问
- [ ] 内部 Topic 副本因子 = 3
- [ ] 防火墙放通 9092（数据）、9093（Controller）

## 与 ZK 模式迁移

使用 `kafka-kraft.sh` 或 Confluent 迁移工具，staging 完整验证后再切生产。

KRaft 减少组件依赖，**新集群优先 KRaft**。
