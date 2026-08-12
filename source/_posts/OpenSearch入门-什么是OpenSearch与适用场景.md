---
title: OpenSearch 入门：什么是 OpenSearch 与适用场景
date: 2026-08-19 09:00:00
tags:
  - OpenSearch
  - 入门
categories:
  - OpenSearch 入门
---

OpenSearch 是一个开源的**分布式搜索与分析引擎**，源自 Elasticsearch 7.10.2 分支，用于全文检索、日志分析和实时数据探索。

## OpenSearch 能做什么

| 场景 | 示例 |
|------|------|
| 全文搜索 | 商品搜索、文档检索 |
| 日志分析 | 应用日志、访问日志、审计 |
| 指标监控 | 系统指标、APM 数据 |
| 安全分析 | SIEM、威胁检测 |
| 数据可视化 | Dashboards 图表与仪表盘 |

## 与相关技术对比

| 技术 | 特点 |
|------|------|
| MySQL LIKE | 慢，不支持复杂 relevance |
| Solr | 老牌搜索，生态较静态 |
| **OpenSearch** | 近实时、分布式、REST API |
| Elasticsearch | 同源，商业版功能差异 |
| ClickHouse | OLAP 更强，全文弱 |

```
数据源 → OpenSearch Index → 搜索/聚合 → Dashboards 展示
```

## 核心概念预览

| 概念 | 类比 |
|------|------|
| Index | 数据库中的表 |
| Document | 表中的一行（JSON） |
| Shard | 索引的分片 |
| Mapping | 表结构/schema |
| Query DSL | 查询语言 |

## 什么时候选 OpenSearch

**适合**：
- 日志集中检索（ELK/EFK 栈）
- 电商/内容全文搜索
- 需要聚合分析的结构化/半结构化数据

**不适合**：
- 强事务 OLTP（用 MySQL/PostgreSQL）
- 纯离线超大 SQL 分析（用 ClickHouse/Spark）
- 小规模简单 KV（用 Redis）

## 学习路线预览

```
概念 → Docker 搭建 → REST API → Mapping → 搜索/聚合
     → 分词 → Dashboards → 日志采集 → 实战 → 排查
```

本系列 20 篇从零带你完成 OpenSearch 入门，无需搜索引擎背景即可上手。
