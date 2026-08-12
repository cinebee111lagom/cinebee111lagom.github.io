---
title: OpenSearch Dashboards 可视化入门
date: 2026-08-19 11:15:00
tags:
  - OpenSearch
  - Dashboards
  - 可视化
categories:
  - OpenSearch 入门
---

OpenSearch Dashboards 是官方可视化界面，用于探索数据、制作图表和仪表盘。

## 首次使用

1. 打开 http://localhost:5601
2. **Stack Management → Index Patterns**（或 Data Sources）
3. 创建 Index Pattern，如 `logs-*`
4. 选择时间字段 `@timestamp`

## Discover（数据探索）

- 选择 Index Pattern
- 时间范围筛选
- 搜索栏支持 KQL/Lucene
- 点击字段筛选、查看文档详情

```
status:500 AND path:/api/*
```

## Visualize（可视化）

| 类型 | 用途 |
|------|------|
| Line | 时序趋势 |
| Bar / Pie | 分布统计 |
| Data Table | 表格聚合 |
| Metric | 单值 KPI |
| Maps | 地理（需 geo_point） |

创建示例：按 `status`  terms 聚合的饼图。

## Dashboard（仪表盘）

- 将多个 Visualization 拖入 Dashboard
- 统一时间选择器
- 保存、分享、导出

## Dev Tools（开发工具）

```
GET /products/_search
{
  "query": { "match_all": {} }
}
```

直接写 Query DSL，新手练习 API 的最佳入口。

## Index Management

- 查看索引列表、存储大小
- 删除旧索引
- 设置 Index State Management（ISM）生命周期

## 快捷键

| 操作 | 说明 |
|------|------|
| Ctrl+Enter | Dev Tools 执行 |
| 时间 picker | 右上角选 last 15m / 24h |

## 与 Kibana 关系

OpenSearch Dashboards  fork 自 Kibana 7.10，界面类似，插件生态独立。

新手路径：**Index Pattern → Discover 探查 → Visualize → Dashboard**。
