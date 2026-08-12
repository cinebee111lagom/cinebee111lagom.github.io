---
title: Flink 窗口（Window）入门：滚动、滑动与会话
date: 2026-08-17 10:00:00
tags:
  - Flink
  - Window
  - 窗口
categories:
  - Flink 新手入门
---

窗口是 Flink 做**实时聚合**的核心机制：把无界流切成有界块再计算。

## 为什么需要窗口

```
无界流：event1, event2, event3, ...
问题：「每分钟订单总额」怎么算？
答案：按 1 分钟切窗口，窗口内 sum(amount)
```

## 窗口类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 滚动 Tumbling | 固定大小、不重叠 | 每 5 分钟统计 |
| 滑动 Sliding | 固定大小、有步长 | 最近 10 分钟、每 1 分钟更新 |
| 会话 Session | 间隔超时切分 | 用户会话时长 |
| 全局 Global | 全流一个窗口 | 需自定义触发 |

## 滚动窗口示例

```java
DataStream<Order> orders = ...;

orders.keyBy(Order::getShopId)
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new OrderAggregateFunction())
    .print();
```

## 滑动窗口

```java
.window(SlidingEventTimeWindows.of(Time.minutes(10), Time.minutes(1)))
// 窗口 10 分钟，每 1 分钟滑动
```

## 计数窗口

```java
.window(TumblingProcessingTimeWindows.of(Time.seconds(10)))
// 或按条数
.countWindow(100)
```

## WindowFunction vs AggregateFunction

```java
// AggregateFunction：增量聚合，省内存（推荐）
.aggregate(new AggregateFunction<Order, Acc, Result>() { ... })

// WindowFunction：拿全量窗口数据，灵活但内存大
.apply(new WindowFunction<Order, Result, String, TimeWindow>() {
    @Override
    public void apply(String key, TimeWindow window,
                      Iterable<Order> input, Collector<Result> out) {
        // 遍历 window 内所有元素
    }
});
```

## 时间类型选择

- **Processing Time**：系统时间，简单但不精确
- **Event Time**：数据自带时间戳，需 Watermark（下篇）

```java
env.setStreamTimeCharacteristic(TimeCharacteristic.EventTime);
```

## 新手建议

1. 先用 **Processing Time + Tumbling** 跑通
2. 生产切 **Event Time + Watermark**
3. 聚合优先 `AggregateFunction`
4. 窗口大小根据业务 SLA（如 1 分钟报表 → 1min 窗口）

窗口 + keyBy 是实时指标类作业的标准组合。
