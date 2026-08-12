---
title: Flink 连接器入门：Kafka 读写
date: 2026-08-17 11:30:00
tags:
  - Flink
  - Kafka
  - Connector
categories:
  - Flink 新手入门
---

Kafka 是 Flink 最常见的数据源与输出，生产作业几乎都会用到。

## Maven 依赖

```xml
<dependency>
  <groupId>org.apache.flink</groupId>
  <artifactId>flink-connector-kafka</artifactId>
  <version>3.2.0-1.19</version>
</dependency>
```

## DataStream 读 Kafka

```java
KafkaSource<String> source = KafkaSource.<String>builder()
    .setBootstrapServers("localhost:9092")
    .setTopics("orders")
    .setGroupId("flink-orders")
    .setStartingOffsets(OffsetsInitializer.earliest())
    .setValueOnlyDeserializer(new SimpleStringSchema())
    .build();

DataStream<String> stream = env.fromSource(
    source,
    WatermarkStrategy.noWatermarks(),
    "kafka-source"
);
```

## DataStream 写 Kafka

```java
KafkaSink<String> sink = KafkaSink.<String>builder()
    .setBootstrapServers("localhost:9092")
    .setRecordSerializer(KafkaRecordSerializationSchema.builder()
        .setTopic("orders-result")
        .setValueSerializationSchema(new SimpleStringSchema())
        .build())
    .setDeliveryGuarantee(DeliveryGuarantee.EXACTLY_ONCE)
    .setTransactionalIdPrefix("flink-orders-")
    .build();

stream.sinkTo(sink);
```

## SQL 方式

```sql
CREATE TABLE kafka_orders (
  order_id STRING,
  user_id  STRING,
  amount   DOUBLE,
  ts       TIMESTAMP(3),
  WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
) WITH (
  'connector' = 'kafka',
  'topic' = 'orders',
  'properties.bootstrap.servers' = 'localhost:9092',
  'properties.group.id' = 'flink-sql',
  'scan.startup.mode' = 'earliest-offset',
  'format' = 'json'
);
```

## 消费起始位置

| 模式 | 说明 |
|------|------|
| earliest-offset | 从头 |
| latest-offset | 最新 |
| group-offsets | 消费者组 committed offset |
| timestamp | 指定时间戳 |

## Exactly-Once 要点

1. 开启 Checkpoint
2. Sink 用 `DeliveryGuarantee.EXACTLY_ONCE`
3. Kafka 事务 ID 前缀唯一
4. `transaction.timeout.ms` > Checkpoint 间隔

## 本地联调

```bash
# 启动 Kafka
docker run -p 9092:9092 apache/kafka:latest

# 发测试数据
kafka-console-producer.sh --topic orders --bootstrap-server localhost:9092
```

## 常见问题

| 问题 | 解决 |
|------|------|
| 无数据 | 检查 group-id、startup.mode |
| 重复消费 | 正常 at-least-once；开 exactly-once |
| 反压 | 提高并行度、优化下游 |

Kafka + Flink 是实时数仓的标准组合，下一篇讲 JDBC/MySQL。
