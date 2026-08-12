---
title: Flink SQL 基础与常用语句
date: 2026-08-17 11:15:00
tags:
  - Flink
  - SQL
categories:
  - Flink 新手入门
---

Flink SQL 让流处理像写数据库查询一样简单，是新手最推荐的入门方式。

## 快速开始

```java
StreamTableEnvironment tableEnv = StreamTableEnvironment.create(env);

tableEnv.executeSql("CREATE TABLE source (...) WITH ('connector'='kafka', ...)");
tableEnv.executeSql("CREATE TABLE sink (...) WITH ('connector'='jdbc', ...)");

tableEnv.executeSql("""
    INSERT INTO sink
    SELECT user_id, COUNT(*) AS cnt
    FROM source
    GROUP BY user_id
""");
```

## 滚动窗口

```sql
SELECT
  user_id,
  TUMBLE_START(event_time, INTERVAL '5' MINUTE) AS window_start,
  SUM(amount) AS total
FROM orders
GROUP BY
  user_id,
  TUMBLE(event_time, INTERVAL '5' MINUTE);
```

## 滑动窗口

```sql
GROUP BY HOP(event_time, INTERVAL '1' MINUTE, INTERVAL '10' MINUTE)
```

## 去重（Top-1）

```sql
SELECT *
FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY user_id ORDER BY event_time DESC
  ) AS rn
  FROM user_events
)
WHERE rn = 1;
```

## JOIN

```sql
-- 流表 JOIN 维表（Lookup Join）
SELECT o.order_id, u.user_name
FROM orders AS o
JOIN users FOR SYSTEM_TIME AS OF o.proc_time AS u
  ON o.user_id = u.user_id;
```

## 时间属性

```sql
CREATE TABLE events (
  id STRING,
  ts TIMESTAMP(3),
  WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
) WITH (...);
```

## SQL Client 交互

```bash
./bin/sql-client.sh

Flink SQL> CREATE TABLE ...;
Flink SQL> SELECT * FROM my_table;
```

## 常用 Connector（WITH 子句）

| connector | 用途 |
|-----------|------|
| kafka | 读写 Kafka |
| jdbc | 读写 MySQL/PostgreSQL |
| elasticsearch-7 | 写 ES |
| filesystem | 读写在离线文件 |
| datagen | 测试数据生成 |

```sql
-- 测试用 datagen
CREATE TABLE gen (
  id STRING,
  val DOUBLE
) WITH (
  'connector' = 'datagen',
  'rows-per-second' = '10'
);
```

## 新手练习

1. datagen → print
2. datagen → 窗口聚合 → print
3. Kafka → SQL 聚合 → Kafka

Flink SQL 覆盖 80% 实时 ETL 场景，复杂 CEP 再学 DataStream。
