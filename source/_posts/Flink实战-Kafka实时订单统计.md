---
title: Flink 实战：Kafka 实时订单统计
date: 2026-08-17 13:15:00
tags:
  - Flink
  - 实战
  - Kafka
categories:
  - Flink 新手入门
---

通过一个完整小项目串联 Kafka、窗口聚合、JDBC Sink。

## 业务需求

```
Kafka topic: orders（JSON）
字段: orderId, userId, shopId, amount, eventTime

输出: 每分钟每店铺订单总额 → MySQL shop_stats
```

## 订单 POJO

```java
public class Order {
    public String orderId;
    public String userId;
    public String shopId;
    public Double amount;
    public Long eventTime;  // epoch ms
}
```

## 完整作业（DataStream）

```java
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
env.enableCheckpointing(60000);

KafkaSource<String> kafkaSource = KafkaSource.<String>builder()
    .setBootstrapServers("localhost:9092")
    .setTopics("orders")
    .setGroupId("flink-shop-stats")
    .setStartingOffsets(OffsetsInitializer.latest())
    .setValueOnlyDeserializer(new SimpleStringSchema())
    .build();

ObjectMapper mapper = new ObjectMapper();

DataStream<Order> orders = env.fromSource(kafkaSource,
    WatermarkStrategy.<String>forBoundedOutOfOrderness(Duration.ofSeconds(5))
        .withTimestampAssigner((s, ts) -> {
            try { return mapper.readValue(s, Order.class).eventTime; }
            catch (Exception e) { return ts; }
        }),
    "kafka")
    .map(s -> mapper.readValue(s, Order.class))
    .filter(o -> o.amount != null && o.amount > 0);

DataStream<Tuple3<String, Double, Long>> stats = orders
    .keyBy(o -> o.shopId)
    .window(TumblingEventTimeWindows.of(Time.minutes(1)))
    .aggregate(
        new AggregateFunction<Order, Double, Double>() {
            public Double createAccumulator() { return 0.0; }
            public Double add(Order v, Double acc) { return acc + v.amount; }
            public Double getResult(Double acc) { return acc; }
            public Double merge(Double a, Double b) { return a + b; }
        },
        new ProcessWindowFunction<Double, Tuple3<String, Double, Long>, String, TimeWindow>() {
            public void apply(String shopId, TimeWindow w, Iterable<Double> in,
                              Collector<Tuple3<String, Double, Long>> out) {
                out.collect(new Tuple3<>(shopId, in.iterator().next(), w.getEnd()));
            }
        }
    );

stats.addSink(JdbcSink.sink(
    "INSERT INTO shop_stats (shop_id, total, window_end) VALUES (?, ?, ?) " +
    "ON DUPLICATE KEY UPDATE total=VALUES(total)",
    (ps, t) -> {
        ps.setString(1, t.f0);
        ps.setDouble(2, t.f1);
        ps.setTimestamp(3, new Timestamp(t.f2));
    },
    JdbcExecutionOptions.builder().withBatchSize(50).build(),
    new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
        .withUrl("jdbc:mysql://localhost:3306/analytics")
        .withDriverName("com.mysql.cj.jdbc.Driver")
        .withUsername("app").withPassword("secret").build()
));

env.execute("Shop Order Stats");
```

## SQL 等价写法

```sql
INSERT INTO shop_stats
SELECT shop_id, SUM(amount), TUMBLE_END(event_time, INTERVAL '1' MINUTE)
FROM kafka_orders
GROUP BY shop_id, TUMBLE(event_time, INTERVAL '1' MINUTE);
```

## 测试数据

```json
{"orderId":"1","userId":"u1","shopId":"s1","amount":99.5,"eventTime":1723957200000}
{"orderId":"2","userId":"u2","shopId":"s1","amount":50.0,"eventTime":1723957205000}
```

## 扩展练习

1. 增加侧输出统计延迟订单
2. 维表 JOIN 店铺名称
3. 结果同时写 Kafka + MySQL

这个案例覆盖 Source → Watermark → Window → Sink 全链路，建议亲手跑通。
