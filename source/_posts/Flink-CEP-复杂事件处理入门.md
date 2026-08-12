---
title: Flink CEP 复杂事件处理入门
date: 2026-08-17 13:00:00
tags:
  - Flink
  - CEP
categories:
  - Flink 新手入门
---

CEP（Complex Event Processing）用于从事件流中检测**模式**，如欺诈、异常登录序列。

## 典型场景

```
规则：10 分钟内同一用户登录失败 3 次 → 告警
规则：下单后 5 分钟内无支付 → 取消提醒
```

## 依赖

```xml
<dependency>
  <groupId>org.apache.flink</groupId>
  <artifactId>flink-cep</artifactId>
  <version>${flink.version}</version>
</dependency>
```

## 基础示例

```java
Pattern<LoginEvent, ?> pattern = Pattern
    .<LoginEvent>begin("first", AfterMatchSkipStrategy.skipPastLastEvent())
    .where(e -> !e.isSuccess())
    .times(3)
    .within(Time.minutes(10));

PatternStream<LoginEvent> patternStream = CEP.pattern(
    loginEvents.keyBy(LoginEvent::getUserId),
    pattern
);

DataStream<Alert> alerts = patternStream.process(new PatternProcessFunction<>() {
    @Override
    public void processMatch(Map<String, List<LoginEvent>> match,
                             Context ctx, Collector<Alert> out) {
        List<LoginEvent> fails = match.get("first");
        out.collect(new Alert(fails.get(0).getUserId(), "3 failures in 10min"));
    }
});
```

## Pattern API

| API | 含义 |
|-----|------|
| `begin` | 模式开始 |
| `next` | 严格连续下一个 |
| `followedBy` | 非严格连续 |
| `followedByAny` | 中间可有无关事件 |
| `times(n)` | 重复 n 次 |
| `within` | 时间窗口 |
| `where` | 条件过滤 |

## 带时间约束

```java
Pattern.<OrderEvent>begin("order")
    .where(e -> e.getType().equals("CREATE"))
    .followedBy("pay")
    .where(e -> e.getType().equals("PAY"))
    .within(Time.minutes(5));
```

## 超时处理

```java
OutputTag<OrderEvent> timeoutTag = new OutputTag<>("timeout"){};

PatternStream<OrderEvent> ps = CEP.pattern(stream, pattern)
    .inEventTime()
    .sideOutputLateData(timeoutTag);

SingleOutputStreamOperator<Result> main = ps.process(...);
DataStream<OrderEvent> timeouts = main.getSideOutput(timeoutTag);
```

## CEP vs SQL

- 简单规则：SQL 窗口 + HAVING 够用
- 复杂序列：CEP Pattern 更直观
- 超高吞吐：注意状态膨胀，合理 within

## 注意

- 必须 `keyBy` 后使用 CEP
- Event Time 需配置 Watermark
- 模式越复杂，状态越大

CEP 是风控、IoT、运维告警的利器，建议在有 Window/State 基础后再学。
