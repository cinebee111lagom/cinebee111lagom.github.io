---
title: OpenSearch SRE 上线 Checklist 与生产 Runbook
date: 2026-08-20 13:45:00
tags:
  - OpenSearch
  - SRE
  - Runbook
categories:
  - OpenSearch SRE
---

## 上线 Checklist

### 架构

- [ ] ≥3 节点，cluster_manager 奇数
- [ ] replicas ≥ 1，跨 AZ awareness
- [ ] 分片规划文档（单 shard 20~50GB）
- [ ] 容量压测：写入、查询 P99

### 配置

- [ ] JVM Xms=Xmx，≤32GB
- [ ] vm.max_map_count=262144
- [ ] auto_create_index: false
- [ ] destructive_requires_name: true
- [ ] 慢日志开启

### 安全

- [ ] Security TLS transport + http
- [ ] RBAC 角色最小权限
- [ ] 默认 admin 密码已改
- [ ] 9200/9300 内网 only

### 备份与生命周期

- [ ] S3 snapshot 仓库 + 日快照
- [ ] ISM 保留策略上线
- [ ] 3 个月内 restore 演练成功

### 监控

- [ ] Prometheus + Grafana
- [ ] red/yellow、磁盘、JVM P0/P1 告警
- [ ] 快照失败告警
- [ ] Runbook 链接

---

## 日常 Runbook

### 集群 red（P0）

```bash
GET /_cluster/health
GET /_cat/shards?v | grep UNASSIGNED
GET /_cluster/allocation/explain
# 恢复节点 / restore snapshot
```

### 磁盘 flood_stage

```bash
GET /_cat/indices?v&s=store.size:desc
# ISM 加速 delete 或扩磁盘
PUT /_all/_settings {"index.blocks.read_only_allow_delete": null}
```

### 节点 down

```bash
systemctl status opensearch
journalctl -u opensearch -n 200
# OOM → 调 heap；磁盘 → 清理
```

### 写入 rejected

- 降 bulk 速率
- 检查 thread_pool write
- 临时增 data 节点

### 慢查询工单

- slowlog 定位 DSL
- profile + hot_threads
- 与开发优化或扩容

### 计划升级

```bash
PUT /_snapshot/s3_repo/pre-upgrade-YYYYMMDD
# 滚动升级节点，见升级篇
```

---

**OpenSearch SRE 系列 20 篇**完结，涵盖部署、HA、快照、ISM、监控、安全、K8s、升级、容量、慢查询、CCR、日志平台、冷热分层与演练。建议配合 **OpenSearch 入门**、**Kafka SRE** 系列对照阅读。
