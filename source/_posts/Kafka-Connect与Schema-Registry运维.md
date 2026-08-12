---
title: Kafka Connect 与 Schema Registry 运维
date: 2026-08-16 12:30:00
tags:
  - Kafka
  - Connect
  - Schema Registry
categories:
  - Kafka SRE
---

Connect 与 Schema Registry 是 Kafka 生态的数据集成层，SRE 需保障其 HA 与兼容性。

## Schema Registry HA

```
3 节点 SR 集群 + Kafka _schemas Topic（RF=3）
```

```properties
kafkastore.topic=_schemas
kafkastore.bootstrap.servers=10.0.1.11:9092
schema.registry.group.id=schema-registry-cluster
host.name=sr1.example.com
listeners=https://0.0.0.0:8081
```

## 兼容性策略

```bash
curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"compatibility": "BACKWARD"}' \
  http://sr:8081/config/orders-value
```

| 策略 | 说明 |
|------|------|
| BACKWARD | 新 schema 可读旧数据（推荐） |
| FORWARD | 旧 consumer 可读新数据 |
| FULL | 双向兼容 |

## Kafka Connect 集群

```properties
bootstrap.servers=10.0.1.11:9092
group.id=connect-cluster
key.converter=io.confluent.connect.avro.AvroConverter
key.converter.schema.registry.url=http://sr:8081
value.converter=io.confluent.connect.avro.AvroConverter
value.converter.schema.registry.url=http://sr:8081
offset.storage.replication.factor=3
config.storage.replication.factor=3
status.storage.replication.factor=3
```

## Connector 运维

```bash
# 创建 JDBC Source
curl -X POST -H "Content-Type: application/json" \
  --data @jdbc-source.json \
  http://connect:8083/connectors

# 状态
curl http://connect:8083/connectors/jdbc-source/status
```

## 常见问题

| 问题 | 排查 |
|------|------|
| Connector FAILED | status API、Connect Worker 日志 |
| Schema 冲突 | SR 兼容性、版本号 |
| 重复消费 | offset 重置、幂等 sink |
| 任务不均衡 | tasks.max、分区数 |

## 监控

- Connect：`connect-worker-metrics` JMX
- SR：`schema-registry-metrics` 请求延迟、注册数
- Lag：`connect-*` internal topics

## 检查清单

- [ ] SR 3 节点 + _schemas RF=3
- [ ] Connect offset/config/status RF=3
- [ ] 兼容性策略按 Topic 配置
- [ ] Connector 变更有 Git 版本管理
- [ ] 升级 SR 与 Connect 版本对齐

Connect 是**数据管道**，故障影响下游 DB/ES，需 P1 监控。
