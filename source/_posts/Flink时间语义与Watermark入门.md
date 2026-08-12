---
title: Flink 时间语义与 Watermark 入门
date: 2026-08-17 10:15:00
tags:
  - Flink
  - Watermark
  - EventTime
categories:
  - Flink 新手入门
---

真实数据常**乱序到达**，Event Time + Watermark 让 Flink 正确处理延迟数据。

## 三种时间

| 时间 | 含义 | 场景 |
|------|------|------|
| Event Time | 数据产生时间 | 生产推荐 |
| Processing Time | 算子处理时间 | 调试、低精度 |
| Ingestion Time | 进入 Flink 时间 | 较少用 |

## 乱序问题

```
实际顺序：  10:00:05 → 10:00:03 → 10:00:07
到达顺序：  10:00:03 → 10:00:07 → 10:00:05（延迟 2s）
```

Event Time 窗口 `[10:00, 10:05)` 应包含 10:00:05 的事件。

## 指定 Event Time 与 Watermark

```java
DataStream<Event> withTimestamps = rawStream
    .assignTimestampsAndWatermarks(
        WatermarkStrategy
            .<Event>forBoundedOutOfOrderness(Duration.ofSeconds(5))
            .withTimestampAssigner((event, ts) -> event.getEventTime())
    );
```

- **Watermark(t)**：表示「时间 ≤ t 的数据已到齐」
- **乱序容忍 5s**：Watermark = 当前最大事件时间 - 5s

## 窗口触发

```
Watermark 推进到 10:05:00 → [10:00, 10:05) 窗口触发计算
```

## 延迟数据处理

```java
.window(TumblingEventTimeWindows.of(Time.minutes(1)))
.allowedLateness(Time.seconds(30))  // 窗口关闭后还等 30s
.sideOutputLateData(lateTag)       // 仍迟到的进侧输出
```

## Processing Time 简化版

```java
// 不需要 Watermark
stream.window(TumblingProcessingTimeWindows.of(Time.minutes(1)))
```

## 新手常见坑

| 坑 | 解决 |
|----|------|
| 窗口无输出 | 检查 Watermark 是否推进（数据源是否停止） |
| 数据被丢 | 增大乱序容忍或 allowedLateness |
| 时间戳为 0 | 确认 timestampAssigner 正确 |
| 时区 | 统一 UTC 或带时区 OffsetDateTime |

## 调试技巧

```java
// 打印当前 Watermark
stream.process(new ProcessFunction<Event, Event>() {
    @Override
    public void processElement(Event e, Context ctx, Collector<Event> out) {
        System.out.println("WM: " + ctx.timerService().currentWatermark());
        out.collect(e);
    }
});
```

生产环境优先 **Event Time + forBoundedOutOfOrderness**，Processing Time 仅用于本地验证。
