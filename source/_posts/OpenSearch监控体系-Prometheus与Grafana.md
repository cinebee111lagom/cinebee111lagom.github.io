---
title: OpenSearch 监控体系：Prometheus 与 Grafana
date: 2026-08-20 10:30:00
tags:
  - OpenSearch
  - Prometheus
  - 监控
categories:
  - OpenSearch SRE
---

OpenSearch 通过 **Performance Analyzer** 或 **Prometheus Exporter** 暴露指标。

## Prometheus Exporter

```yaml
# docker-compose 侧车或独立部署
scrape_configs:
  - job_name: opensearch
    static_configs:
      - targets: ['os-1:9200', 'os-2:9200', 'os-3:9200']
    metrics_path: /_prometheus/metrics
    scheme: https
    basic_auth:
      username: admin
      password: xxx
```

需安装 `prometheus-exporter` 插件或使用社区 elasticsearch_exporter（兼容 API）。

## 核心指标

| 指标 | 含义 | 告警 |
|------|------|------|
| `cluster_health_status` | green=0,yellow=1,red=2 | red P0 |
| `opensearch_jvm_memory_used_bytes` | JVM 使用 | >85% P1 |
| `opensearch_cluster_shards_unassigned` | 未分配分片 | >0 P0 |
| `opensearch_indices_search_query_time_seconds` | 查询耗时 | P99 突增 |
| `opensearch_indices_indexing_index_total` | 写入量 | 突降 |
| `opensearch_fs_total_available_bytes` | 磁盘可用 | <15% P1 |

## CAT API 巡检脚本

```bash
curl -s -ku admin:pass https://os-1:9200/_cat/health?v
curl -s -ku admin:pass https://os-1:9200/_cat/indices?v&s=store.size:desc
curl -s -ku admin:pass https://os-1:9200/_cat/thread_pool/write?v
```

## Grafana Dashboard

- 社区 OpenSearch/Elasticsearch Dashboard 适配
- 面板：集群健康、JVM、GC、搜索/索引速率、磁盘

## 日志

```
/var/log/opensearch/prod-opensearch.log
/var/log/opensearch/prod-opensearch_index_indexing_slowlog.log
/var/log/opensearch/prod-opensearch_index_search_slowlog.log
```

→ Loki/ELK 集中采集。

## 检查清单

- [ ] 每节点 metrics 被抓取
- [ ] red/yellow、磁盘、JVM P0/P1 告警
- [ ] 慢查询日志开启
- [ ] Dashboard 按集群/索引分视图
- [ ] 告警带 Runbook 链接

监控铁三角：**health + disk + JVM**。
