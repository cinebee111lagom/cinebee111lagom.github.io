---
title: Flink 新手学习路径与入门 Checklist
date: 2026-08-17 13:45:00
tags:
  - Flink
  - 入门
  - 学习路径
categories:
  - Flink 新手入门
---

## 推荐学习路径

```
第 1 周：概念 + 环境 + WordCount
  └─ 篇 1~3

第 2 周：DataStream API + 窗口 + Watermark
  └─ 篇 4~6

第 3 周：State + Checkpoint + SQL
  └─ 篇 7~10

第 4 周：Kafka/JDBC 连接器 + 实战案例
  └─ 篇 11~14、18

第 5 周：并行度/反压/K8s 部署（可选深入）
  └─ 篇 15~17、19~20
```

## 入门 Checklist

### 基础

- [ ] 本地 Standalone 或 IDE 跑通 WordCount
- [ ] 理解 Source → Transform → Sink
- [ ] 会用 keyBy + 滚动窗口做聚合
- [ ] 理解 Event Time 与 Watermark 作用

### 进阶

- [ ] 写过 KeyedProcessFunction + ValueState
- [ ] 开启 Checkpoint 并从 Web UI 观察
- [ ] 用 Flink SQL 完成窗口聚合
- [ ] Kafka Source/Sink 跑通端到端

### 实战

- [ ] 完成「实时订单统计」案例
- [ ] JDBC 或 CDC 写 MySQL 成功
- [ ] 能读 Web UI 反压与 Checkpoint
- [ ] 独立排查「无输出」类问题

### 生产意识（了解即可）

- [ ] Exactly-Once 三要素
- [ ] 并行度与 Kafka 分区关系
- [ ] Savepoint 升级概念

## 配套练习

| 练习 | 技能点 |
|------|--------|
| 实时词频 Top 10 | window + aggregate |
| 用户 5 分钟去重 UV | set state / SQL distinct |
| 订单 JOIN 用户维表 | Lookup Join |
| 登录失败 3 次告警 | CEP |
| 文件批处理 + Kafka 流统一 SQL | 批流一体 |

## 推荐资源

- 官方文档：https://flink.apache.org/docs/
- Flink Forward 视频（概念进阶）
- 本地 Docker Compose：Kafka + Flink + MySQL

## 与 SRE 系列衔接

学完本系列后，可继续深入：
- Flink 作业运维与监控（Prometheus）
- Savepoint 升级与状态兼容
- 大状态调优与 RocksDB

---

**Flink 新手入门系列 20 篇**完结，从零到能独立写出 Kafka → 窗口聚合 → MySQL 的实时作业。建议配合 **Kafka SRE** 系列理解数据源侧，配合 **MySQL SRE** 系列理解结果落库侧。
