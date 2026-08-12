---
title: OpenSearch 日志平台运维最佳实践
date: 2026-08-20 13:00:00
tags:
  - OpenSearch
  - 日志平台
categories:
  - OpenSearch SRE
---

日志平台是 OpenSearch 最大应用场景，SRE 需标准化采集、索引与治理。

## 标准架构

```
App → Filebeat/Fluent Bit → OpenSearch
                         ↘ Logstash（复杂 grok）
Dashboards ← Index Pattern ← logs-<app>-YYYY.MM.DD
```

## 索引命名规范

```
logs-<team>-<app>-YYYY.MM.DD
例：logs-payment-order-svc-2026.08.20
```

## Index Template

```bash
PUT /_index_template/logs-app-template
{
  "index_patterns": ["logs-*-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "5s",
      "index.codec": "best_compression"
    },
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "message": { "type": "text" },
        "level": { "type": "keyword" },
        "service": { "type": "keyword" },
        "trace_id": { "type": "keyword" }
      }
    }
  }
}
```

## 写入别名

```
logs-app-write → 当日索引（is_write_index: true）
Filebeat index 名固定写别名
```

## ISM 30 天保留

见 ISM 篇，delete 前 snapshot。

## 多租户

| 方式 | 说明 |
|------|------|
| 索引隔离 | 每 team 独立 index pattern |
| DLS | Security 文档级隔离 |
| 专用集群 | 大租户独立 |

## 常见问题治理

| 问题 | 方案 |
|------|------|
| mapping 爆炸 | 限制 dynamic mapping，用 flattened |
| 日志风暴 | Filebeat 采样 / rate limit |
| 热字段过多 | 结构化 logging（JSON） |
| 查询慢 | 时间范围必选 + filter |

## Onboarding 流程

1. 团队申请 index pattern + 保留天数
2. SRE 创建 template + ISM + RBAC
3. 提供 Filebeat 配置片段
4. Dashboards 空间授权

## Checklist

- [ ] 所有日志走 template
- [ ] 无 default _index
- [ ] 保留天数 ISM  enforced
- [ ] 磁盘容量月度 forecast

日志平台 SRE 核心是 **标准化 + 生命周期 + 成本**。
