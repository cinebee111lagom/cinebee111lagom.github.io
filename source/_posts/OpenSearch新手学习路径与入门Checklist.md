---
title: OpenSearch 新手学习路径与入门 Checklist
date: 2026-08-19 13:45:00
tags:
  - OpenSearch
  - 入门
  - 学习路径
categories:
  - OpenSearch 入门
---

## 推荐学习路径

```
第 1 周：概念 + Docker + REST API + CRUD
  └─ 篇 1~6

第 2 周：Mapping + 搜索 + 聚合 + 分词
  └─ 篇 5~9

第 3 周：Dashboards + 模板/别名 + 集群概念
  └─ 篇 10~12

第 4 周：Bulk 导入 + Filebeat + 实战案例
  └─ 篇 13~14、18

第 5 周：SQL/PPL + 安全 + 性能 + 排查
  └─ 篇 15~17、19~20
```

## 入门 Checklist

### 基础

- [ ] Docker 单节点跑通，9200/5601 可访问
- [ ] 理解 Index / Document / Shard
- [ ] 会用 curl 完成 CRUD
- [ ] 能写 match + term + bool 查询
- [ ] 能写 terms / date_histogram 聚合

### 进阶

- [ ] 设计 text + keyword 双字段 mapping
- [ ] 创建 Index Template
- [ ] Dashboards 创建 Index Pattern + Discover
- [ ] Bulk 导入 1 万条测试数据
- [ ] Filebeat 采集日志到 OpenSearch

### 实战

- [ ] 完成 Nginx 日志分析案例
- [ ] 做一个 Dashboard（≥3 图表）
- [ ] 会用 `/_cluster/health` 和 `/_cat/shards` 排查
- [ ] 了解 Security 基本认证

### 延伸（后续可学）

- Snapshot 备份恢复
- Cross-Cluster Search
- OpenSearch SRE 运维系列

## 配套练习

| 练习 | 技能点 |
|------|--------|
| 商品搜索 mini | mapping + match + filter |
| 日志 5xx 统计 | aggregation + Dashboards |
| 按日滚索引 | template + alias |
| 中文分词对比 | analyze API + smartcn |
| SQL 转 DSL | `_sql/_explain` |

## 推荐资源

- 官方文档：https://docs.opensearch.org/
- Dashboards Dev Tools 动手练习
- 配合 **Kafka SRE** 理解日志上游

---

**OpenSearch 入门系列 20 篇**完结，从零到能独立搭建日志检索、完成 Dashboard 分析。下一步可深入安全、快照备份与集群运维。
