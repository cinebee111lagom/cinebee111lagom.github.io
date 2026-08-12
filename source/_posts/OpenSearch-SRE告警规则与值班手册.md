---
title: OpenSearch SRE 告警规则与值班手册
date: 2026-08-20 10:45:00
tags:
  - OpenSearch
  - SRE
  - 告警
categories:
  - OpenSearch SRE
---

OpenSearch 告警需覆盖集群、节点、索引与快照四个层次。

## 告警分级

| 级别 | 场景 | 响应 |
|------|------|------|
| P0 | 集群 red、快照连续失败 | 5 分钟 |
| P1 | yellow 持续、磁盘 >85%、JVM >90% | 15 分钟 |
| P2 | 慢查询激增、bulk reject | 1 小时 |
| P3 | 证书过期、ISM 未执行 | 工作日 |

## Prometheus 规则示例

```yaml
groups:
  - name: opensearch
    rules:
      - alert: OpenSearchClusterRed
        expr: opensearch_cluster_status == 2
        for: 2m
        labels:
          severity: critical

      - alert: OpenSearchDiskLow
        expr: opensearch_fs_total_available_bytes / opensearch_fs_total_total_bytes < 0.15
        for: 10m
        labels:
          severity: warning

      - alert: OpenSearchJVMHigh
        expr: opensearch_jvm_memory_used_bytes / opensearch_jvm_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: warning

      - alert: OpenSearchUnassignedShards
        expr: opensearch_cluster_shards_unassigned > 0
        for: 5m
        labels:
          severity: critical
```

## 值班速查

### 集群 red

```bash
GET /_cluster/health
GET /_cat/shards?v | grep UNASSIGNED
GET /_cluster/allocation/explain
# 恢复节点 / restore snapshot
```

### 磁盘 flood_stage

```bash
GET /_cat/indices?v&s=store.size:desc
DELETE /old-logs-2026.06.*
PUT /_all/_settings { "index.blocks.read_only_allow_delete": null }
```

### 写入 429

- 线程池 write rejected → 降 bulk 速率、扩节点
- circuit breaker → 减 aggregation 复杂度

### 查询慢

- 查 slowlog
- `_nodes/hot_threads`
- Profile 慢 DSL

### 节点 down

1. 检查进程/容器/K8s pod
2. 查 OOM、dmesg
3. 替换节点，等待 shard reassign

## On-Call 原则

1. red 优先 restore 数据可用性
2. 删索引前确认 ISM/备份
3. 变更索引 mapping 需 reindex 计划
4. 48h Postmortem

每季度 review 告警，减少 yellow 误报噪音。
