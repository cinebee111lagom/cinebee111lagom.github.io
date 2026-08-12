---
title: Flink 常见问题与调试技巧
date: 2026-08-17 13:30:00
tags:
  - Flink
  - 调试
  - 常见问题
categories:
  - Flink 新手入门
---

新手跑 Flink 作业常踩这些坑，本文汇总排查思路。

## 作业不跑 / 无输出

| 原因 | 检查 |
|------|------|
| 未调用 execute() | main 末尾 `env.execute()` |
| Source 无数据 | Kafka group、offset、topic |
| 窗口不触发 | Watermark 未推进（Event Time） |
| filter 全过滤 | 打印中间流 `.print()` |

## 序列化错误

```
java.io.NotSerializableException
```

- Lambda 引用外部非 serializable 对象
- 解决：static 字段、RichFunction 的 open() 初始化

## ClassNotFoundException

- Connector 未打进 jar
- 用 `maven-shade-plugin` 打包 fat jar
- 或放到 Flink `lib/` 目录

## 时间相关

```
窗口结果不对 / 少数据
```

- 确认 Event Time 字段与时区
- 乱序容忍是否够
- Processing Time 与 Event Time 混用

## Checkpoint 失败

```bash
# 日志搜
Checkpoint expired
Alignment timeout
```

- 增大 `checkpointTimeout`
- 检查反压、TM 内存
- RocksDB 大状态用增量 Checkpoint

## 内存 OOM

- 增大 TM memory
- 检查是否 window 全量 `WindowFunction` 攒数据
- State TTL 是否开启
- `enableObjectReuse` 误用导致对象膨胀

## 本地调试技巧

```java
// 1. 并行度 1
env.setParallelism(1);

// 2. 打印中间结果
stream.map(...).print();

// 3. 用 datagen 替代 Kafka
tableEnv.executeSql("CREATE TABLE gen (...) WITH ('connector'='datagen')");

// 4. 远程调试
env.getConfig().setAutoWatermarkInterval(200);  // 加快 WM
```

## Web UI 必看

- **Overview**：状态、Checkpoint
- **TaskManagers**：内存、GC
- **Back Pressure**：瓶颈算子
- **Exceptions**：失败堆栈

## 日志级别

```yaml
# log4j.properties
logger.flink.name = org.apache.flink
logger.flink.level = INFO
# 调试某算子
logger.myapp.name = com.example
logger.myapp.level = DEBUG
```

**万能法则**：二分法 `.print()` 定位哪一步丢了数据。
