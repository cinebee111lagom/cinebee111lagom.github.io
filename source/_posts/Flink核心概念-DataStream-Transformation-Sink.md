---
title: Flink 核心概念：DataStream、Transformation、Sink
date: 2026-08-17 09:30:00
tags:
  - Flink
  - DataStream
categories:
  - Flink 新手入门
---

理解 DataStream 编程模型，是写好 Flink 作业的基础。

## 数据流模型

```
Source → Transformation → Transformation → Sink
```

- **Source**：产生数据（Kafka、Socket、Collection）
- **Transformation**：转换（map、filter、keyBy、window）
- **Sink**：输出（print、Kafka、JDBC、ES）

## 常用 Transformation

| 算子 | 作用 | 示例 |
|------|------|------|
| `map` | 1 进 1 出 | 解析 JSON |
| `flatMap` | 1 进 N 出 | 拆词、拆数组 |
| `filter` | 过滤 | 过滤空值 |
| `keyBy` | 按 key 分区 | 按 userId 分组 |
| `reduce` / `sum` | 聚合 | 计数、求和 |
| `union` | 合并流 | 多源合并 |
| `connect` | 连接双流 | 流 join |

## 代码示例

```java
DataStream<Event> events = env
    .socketTextStream("localhost", 9999)
    .map(json -> parseEvent(json))
    .filter(e -> e != null && e.getUserId() != null);

DataStream<Long> perUser = events
    .keyBy(Event::getUserId)
    .map(e -> 1L)
    .sum(0);
```

## 并行度

```java
env.setParallelism(4);           // 全局默认
stream.map(...).setParallelism(2); // 单算子
```

```
并行度 4 = 4 个 Task 并行处理
keyBy 后相同 key 到同一 subtask
```

## Sink 示例

```java
// 开发调试
stream.print();

// 写入 Kafka
stream.sinkTo(kafkaSink);

// 写入文件
stream.sinkTo(FileSink.forRowFormat(...).build());
```

## 执行模式

| 模式 | 说明 |
|------|------|
| `STREAMING` | 默认，无界流 |
| `BATCH` | 有界批处理 |
| `AUTOMATIC` | 自动检测 |

```java
env.setRuntimeMode(RuntimeExecutionMode.STREAMING);
```

## 注意事项

- `keyBy` 之后才能做 keyed 聚合
- Transformation 是**懒执行**，`execute()` 才真正跑
- 每条 DataStream 有类型信息，复杂类型需 `TypeInformation`

掌握 Source → Transform → Sink 三段式，就掌握了 Flink 程序骨架。
