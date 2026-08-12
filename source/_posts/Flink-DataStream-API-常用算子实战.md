---
title: Flink DataStream API 常用算子实战
date: 2026-08-17 09:45:00
tags:
  - Flink
  - DataStream
  - API
categories:
  - Flink 新手入门
---

DataStream API 是 Flink 最灵活的编程接口，本节梳理新手最常用的算子。

## map 与 flatMap

```java
// map：一行转 Event
DataStream<Event> events = rawStream.map(line -> {
    ObjectMapper mapper = new ObjectMapper();
    return mapper.readValue(line, Event.class);
});

// flatMap：一条变多条
DataStream<String> words = lines.flatMap((String line, Collector<String> out) -> {
    for (String w : line.split(" ")) {
        out.collect(w);
    }
});
```

## filter

```java
DataStream<Event> valid = events.filter(e ->
    e.getAmount() != null && e.getAmount() > 0
);
```

## keyBy 与聚合

```java
// Tuple 按字段
stream.keyBy(0).sum(1);

// POJO 按属性
events.keyBy(Event::getUserId)
    .reduce((a, b) -> {
        a.setAmount(a.getAmount() + b.getAmount());
        return a;
    });
```

## 多流合并

```java
// union：同类型
DataStream<String> merged = streamA.union(streamB);

// connect + CoProcessFunction：不同类型双流
streamA.connect(streamB)
    .keyBy(a -> a.getId(), b -> b.getId())
    .process(new MyCoProcessFunction());
```

## 侧输出（Side Output）

```java
OutputTag<String> lateTag = new OutputTag<>("late-data"){};

SingleOutputStreamOperator<Result> main = stream
    .process(new ProcessFunction<Event, Result>() {
        @Override
        public void processElement(Event e, Context ctx, Collector<Result> out) {
            if (isLate(e)) {
                ctx.output(lateTag, e.toString());
            } else {
                out.collect(toResult(e));
            }
        }
    });

DataStream<String> late = main.getSideOutput(lateTag);
```

## ProcessFunction（最灵活）

```java
stream.keyBy(Event::getUserId)
    .process(new KeyedProcessFunction<String, Event, Alert>() {
        private ValueState<Integer> countState;

        @Override
        public void open(Configuration parameters) {
            countState = getRuntimeContext().getState(
                new ValueStateDescriptor<>("count", Integer.class));
        }

        @Override
        public void processElement(Event e, Context ctx, Collector<Alert> out)
                throws Exception {
            int c = countState.value() == null ? 0 : countState.value();
            countState.update(c + 1);
            if (c + 1 > 10) {
                out.collect(new Alert(e.getUserId(), "too many events"));
            }
        }
    });
```

## 算子选择建议

| 需求 | 算子 |
|------|------|
| 简单转换 | map / filter |
| 拆分 | flatMap |
| 分组聚合 | keyBy + sum/reduce |
| 定时/状态逻辑 | KeyedProcessFunction |
| 分流 | Side Output |

下一篇讲窗口（Window），是实时聚合的核心。
