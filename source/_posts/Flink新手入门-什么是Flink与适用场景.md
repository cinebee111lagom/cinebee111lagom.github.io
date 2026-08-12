---
title: Flink 新手入门：什么是 Flink 与适用场景
date: 2026-08-17 09:00:00
tags:
  - Flink
  - 入门
categories:
  - Flink 新手入门
---

Apache Flink 是一个**分布式流处理框架**，核心能力是：低延迟处理无界数据流，并支持批流一体。

## Flink 能做什么

| 场景 | 示例 |
|------|------|
| 实时 ETL | Kafka → 清洗 → 写入 OLAP |
| 实时指标 | 每分钟 PV/UV、订单量 |
| 实时风控 | 支付欺诈检测 |
| 实时推荐 | 用户行为触发特征更新 |
| 复杂事件 | 登录异常、设备切换告警（CEP） |

## 与相关技术对比

| 技术 | 特点 |
|------|------|
| Kafka | 消息队列/事件存储，不做计算 |
| Spark Streaming | 微批，延迟通常秒级 |
| **Flink** | 真流处理，延迟毫秒~秒级 |
| Storm | 早期流处理，生态已弱 |

```
数据源(Kafka/MySQL CDC) → Flink 计算 → 结果(Sink 到 ES/Redis/DB)
```

## 核心优势

- **Exactly-Once**：Checkpoint 保证端到端语义
- **Event Time**：按业务时间处理乱序数据
- **状态管理**：内置 Keyed State，支持大状态
- **批流一体**：同一套 API 处理有界/无界数据

## 什么时候选 Flink

**适合**：
- 延迟要求秒级以内
- 需要窗口聚合、CEP、状态计算
- 已有 Kafka 等流数据源

**不适合**：
- 纯离线 T+1 报表（Spark/Hive 更简单）
- 数据量极小、逻辑极简单（直接用应用消费 Kafka）

## 学习路线预览

```
概念 → 环境 → DataStream API → 窗口/Watermark → State/Checkpoint
     → Table/SQL → Kafka 连接器 → 实战案例 → 部署调优
```

本系列 20 篇从零带你走完 Flink 入门路径，无需分布式背景即可上手。
