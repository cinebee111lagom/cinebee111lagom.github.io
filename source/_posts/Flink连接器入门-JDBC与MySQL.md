---
title: Flink 连接器入门：JDBC 与 MySQL
date: 2026-08-17 11:45:00
tags:
  - Flink
  - JDBC
  - MySQL
categories:
  - Flink 新手入门
---

JDBC Connector 用于 Flink 读写 MySQL/PostgreSQL，常用于维表关联与结果落库。

## 依赖

```xml
<dependency>
  <groupId>org.apache.flink</groupId>
  <artifactId>flink-connector-jdbc</artifactId>
  <version>3.2.0-1.19</version>
</dependency>
<dependency>
  <groupId>com.mysql</groupId>
  <artifactId>mysql-connector-j</artifactId>
  <version>8.3.0</version>
</dependency>
```

## SQL 写 MySQL（Sink）

```sql
CREATE TABLE result_sink (
  user_id STRING,
  total_amount DOUBLE,
  window_end TIMESTAMP(3),
  PRIMARY KEY (user_id, window_end) NOT ENFORCED
) WITH (
  'connector' = 'jdbc',
  'url' = 'jdbc:mysql://localhost:3306/analytics',
  'table-name' = 'user_order_stats',
  'username' = 'app',
  'password' = 'secret',
  'sink.buffer-flush.max-rows' = '100',
  'sink.buffer-flush.interval' = '5s'
);

INSERT INTO result_sink
SELECT user_id, SUM(amount), TUMBLE_END(ts, INTERVAL '1' MINUTE)
FROM orders
GROUP BY user_id, TUMBLE(ts, INTERVAL '1' MINUTE);
```

## Lookup Join（维表）

```sql
CREATE TABLE users (
  user_id STRING,
  user_name STRING,
  PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
  'connector' = 'jdbc',
  'url' = 'jdbc:mysql://localhost:3306/db',
  'table-name' = 'users',
  'lookup.cache.max-rows' = '10000',
  'lookup.cache.ttl' = '1h'
);

SELECT o.order_id, u.user_name, o.amount
FROM orders AS o
JOIN users FOR SYSTEM_TIME AS OF o.proc_time AS u
  ON o.user_id = u.user_id;
```

## DataStream JDBC Sink

```java
JdbcSink.sink(
    "INSERT INTO stats (user_id, cnt) VALUES (?, ?)",
    (ps, t) -> {
        ps.setString(1, t.f0);
        ps.setLong(2, t.f1);
    },
    JdbcExecutionOptions.builder()
        .withBatchSize(100)
        .withBatchIntervalMs(5000)
        .build(),
    new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
        .withUrl("jdbc:mysql://localhost:3306/db")
        .withDriverName("com.mysql.cj.jdbc.Driver")
        .withUsername("app")
        .withPassword("secret")
        .build()
);
```

## CDC 读 MySQL（变更捕获）

实时同步用 **Flink CDC** 而非轮询 JDBC：

```xml
<dependency>
  <groupId>com.ververica</groupId>
  <artifactId>flink-connector-mysql-cdc</artifactId>
  <version>3.1.0</version>
</dependency>
```

```sql
CREATE TABLE orders_cdc (
  order_id STRING,
  amount DOUBLE,
  PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
  'connector' = 'mysql-cdc',
  'hostname' = 'localhost',
  'port' = '3306',
  'username' = 'repl',
  'password' = 'secret',
  'database-name' = 'shop',
  'table-name' = 'orders'
);
```

## 注意

- JDBC Sink 批量刷写，注意主键与幂等
- Lookup 缓存防打爆 DB
- 大表同步优先 CDC，非 `SELECT *` 轮询
