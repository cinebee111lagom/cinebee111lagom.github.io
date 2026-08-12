---
title: Flink 状态（State）入门：Keyed State 与 Operator State
date: 2026-08-17 10:30:00
tags:
  - Flink
  - State
  - 状态
categories:
  - Flink 新手入门
---

有状态的计算是 Flink 区别于简单消息消费的核心能力。

## 为什么需要状态

```
场景：统计每个用户最近 1 小时点击次数
→ 需要记住「每个 userId 的计数」→ Keyed State
```

## Keyed State（最常用）

必须在 `keyBy` 之后使用：

```java
public class CountWithState extends KeyedProcessFunction<String, Event, Tuple2<String, Long>> {

    private ValueState<Long> countState;

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<Long> desc =
            new ValueStateDescriptor<>("count", Long.class);
        countState = getRuntimeContext().getState(desc);
    }

    @Override
    public void processElement(Event e, Context ctx, Collector<Tuple2<String, Long>> out)
            throws Exception {
        Long count = countState.value();
        if (count == null) count = 0L;
        count = count + 1;
        countState.update(count);
        out.collect(new Tuple2<>(e.getUserId(), count));
    }
}

// 使用
events.keyBy(Event::getUserId).process(new CountWithState());
```

## State 类型

| 类型 | 用途 |
|------|------|
| ValueState | 单值（计数、最新时间） |
| ListState | 列表（历史记录） |
| MapState | KV 映射 |
| ReducingState / AggregatingState | 增量聚合 |

## Operator State

绑定在算子实例上，非 key 维度：

```java
public class BufferingSink implements CheckpointedFunction {
    private ListState<Event> buffered;

    @Override
    public void snapshotState(FunctionSnapshotContext context) {
        buffered.update(bufferList);
    }

    @Override
    public void initializeState(FunctionInitializationContext context) {
        buffered = context.getOperatorStateStore()
            .getListState(new ListStateDescriptor<>("buf", Event.class));
    }
}
```

## 状态 TTL（过期）

```java
StateTtlConfig ttl = StateTtlConfig
    .newBuilder(Time.hours(24))
    .setUpdateType(StateTtlConfig.UpdateType.OnCreateAndWrite)
    .build();
desc.enableTimeToLive(ttl);
```

## 状态后端

| 后端 | 特点 |
|------|------|
| HashMapStateBackend | 内存，小状态 |
| EmbeddedRocksDBStateBackend | 磁盘，大状态 |

```java
env.setStateBackend(new EmbeddedRocksDBStateBackend());
```

## 注意

- State 过大 → 用 RocksDB + 合理 TTL
- 改 State 结构需考虑兼容性（State Migration）
- Keyed State 与 keyBy 字段强绑定

下一篇讲 Checkpoint，状态如何容错恢复。
