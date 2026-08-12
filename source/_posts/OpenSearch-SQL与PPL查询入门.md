---
title: OpenSearch SQL 与 PPL 查询入门
date: 2026-08-19 12:30:00
tags:
  - OpenSearch
  - SQL
  - PPL
categories:
  - OpenSearch 入门
---

不习惯 Query DSL？OpenSearch 支持 **SQL** 和 **PPL** 两种声明式查询语言。

## SQL 插件

```bash
# 安装（部分发行版内置）
bin/opensearch-plugin install opensearch-sql

# JDBC 驱动也可连 BI 工具
```

### REST 查询

```bash
POST /_plugins/_sql
{
  "query": "SELECT title, price FROM products WHERE price > 50 ORDER BY price DESC LIMIT 10"
}
```

```bash
# 转为 DSL（学习用）
POST /_plugins/_sql/_explain
{
  "query": "SELECT count(*) FROM products"
}
```

## Dashboards SQL Workbench

**OpenSearch Dashboards → Query Workbench → SQL**，可视化执行与导出。

## PPL（Pipe Processing Language）

类 Unix 管道语法，适合日志探索：

```bash
POST /_plugins/_ppl
{
  "query": "source=logs-* | where status >= 500 | stats count() by host"
}
```

```
source=index
| where 条件
| fields 字段
| stats agg by 分组
| sort 字段
| head N
```

## SQL vs DSL vs PPL

| | SQL | Query DSL | PPL |
|---|-----|-----------|-----|
| 受众 | BI/SQL 背景 | 开发者/API | 日志分析 |
| 功能 | 子集 | 最全 | 日志友好 |
| 性能 | 部分转 DSL | 原生 | 部分场景 |

## 限制（SQL）

- 不支持所有 DSL 特性（如复杂 nested）
- 超大结果需 cursor 分页
- 生产复杂查询仍推荐 DSL

## 示例对照

**DSL**：
```json
{ "query": { "range": { "price": { "gt": 50 } } } }
```

**SQL**：
```sql
SELECT * FROM products WHERE price > 50
```

**PPL**：
```
source=products | where price > 50
```

新手可用 SQL/PPL 快速验证数据，深入优化再学 DSL。
