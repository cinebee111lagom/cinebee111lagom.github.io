---
title: Flink 批流一体：Batch 与 Streaming 模式
date: 2026-08-17 12:00:00
tags:
  - Flink
  - 批流一体
categories:
  - Flink 新手入门
---

Flink 同一套 API 可跑**无界流**（Streaming）和**有界数据集**（Batch）。

## 执行模式

```java
// 流模式（默认）
env.setRuntimeMode(RuntimeExecutionMode.STREAMING);

// 批模式
env.setRuntimeMode(RuntimeExecutionMode.BATCH);

// 自动：有界 Source 用 Batch，无界用 Streaming
env.setRuntimeMode(RuntimeExecutionMode.AUTOMATIC);
```

## 有界 Source 示例

```java
// 读文件（有界）
FileSource<String> fileSource = FileSource.forRecordStreamFormat(
    new TextLineInputFormat(), new Path("/data/orders")).build();

env.fromSource(fileSource, WatermarkStrategy.noWatermarks(), "file");

// 批模式下一次跑完退出
env.setRuntimeMode(RuntimeExecutionMode.BATCH);
env.execute("batch-job");
```

## 流 vs 批差异

| | Streaming | Batch |
|---|-----------|-------|
| 输入 | 无界（Kafka） | 有界（文件、表快照） |
| 调度 | 长期运行 | 跑完结束 |
| 窗口 | 时间驱动 | 可全局聚合 |
| Checkpoint | 必须 | 可选 |
| 延迟 | 毫秒~秒 | 分钟~小时 |

## SQL 批流统一

```sql
-- 同一 SQL，有界表自动批执行
SELECT region, SUM(sales) FROM sales_batch GROUP BY region;
```

```sql
-- 无界 Kafka 表流执行
SELECT region, SUM(sales) FROM sales_stream GROUP BY region;
```

## lambda 架构简化

```
传统：Spark 批 + Flink 流 两套逻辑
批流一体：Flink SQL 一套逻辑，换 Source 即可
```

## 何时用 Batch 模式

- 离线补数、历史回刷
- 有界文件/Hive 表一次性统计
- 开发调试小数据集

## 何时用 Streaming

- Kafka 实时消费
- CDC 实时同步
- 7×24 在线指标

## 新手建议

1. 实时作业一律 **Streaming + Checkpoint**
2. 补数任务用 **Batch** 读历史文件
3. SQL 作业优先 **AUTOMATIC**，让 Flink 判断

批流一体是 Flink 相对 Spark 的差异化能力之一。
