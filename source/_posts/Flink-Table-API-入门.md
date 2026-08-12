---
title: Flink Table API 入门
date: 2026-08-17 11:00:00
tags:
  - Flink
  - Table API
categories:
  - Flink 新手入门
---

Table API 是 Flink 的**声明式**接口，用关系代数操作流/表，底层仍编译为 DataStream。

## 依赖

```xml
<dependency>
  <groupId>org.apache.flink</groupId>
  <artifactId>flink-table-api-java-bridge</artifactId>
  <version>${flink.version}</version>
</dependency>
```

## 环境创建

```java
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
StreamTableEnvironment tableEnv = StreamTableEnvironment.create(env);
```

## 从 DataStream 注册表

```java
DataStream<Order> orders = ...;

tableEnv.createTemporaryView("orders", orders,
    $("orderId"), $("userId"), $("amount"), $("eventTime").rowtime());

Table result = tableEnv.from("orders")
    .groupBy($("userId"))
    .select($("userId"), $("amount").sum().as("total"));

DataStream<OrderSum> out = tableEnv.toDataStream(result, OrderSum.class);
```

## 从 DDL 建表

```java
tableEnv.executeSql("""
    CREATE TABLE orders (
      order_id STRING,
      user_id  STRING,
      amount   DOUBLE,
      ts       TIMESTAMP(3),
      WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
    ) WITH (
      'connector' = 'kafka',
      'topic' = 'orders',
      'properties.bootstrap.servers' = 'localhost:9092',
      'format' = 'json'
    )
""");
```

## 常用操作

```java
// 过滤
tableEnv.from("orders").filter($("amount").isGreater(100));

// 窗口（Table 窗口语法见 SQL 篇）
tableEnv.executeSql("""
    SELECT user_id, TUMBLE_START(ts, INTERVAL '1' MINUTE) AS w_start,
           SUM(amount) AS total
    FROM orders
    GROUP BY user_id, TUMBLE(ts, INTERVAL '1' MINUTE)
""");
```

## Table API vs DataStream

| | Table API | DataStream |
|---|-----------|------------|
| 风格 | 声明式、SQL 友好 | 命令式、灵活 |
| 状态/CEP | 部分场景受限 | 完全控制 |
| 学习曲线 | SQL 背景友好 | Java 背景友好 |
| 推荐 | ETL、指标 SQL 化 | 复杂事件、自定义逻辑 |

## 类型与 Schema

Flink 自动推断 POJO 字段；复杂类型用 `@DataTypeHint` 或 Schema 显式声明。

Table API 与 SQL 可混用，**新手优先 SQL**，复杂逻辑再落 DataStream。
