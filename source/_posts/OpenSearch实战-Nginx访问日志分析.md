---
title: OpenSearch 实战：Nginx 访问日志分析
date: 2026-08-19 13:15:00
tags:
  - OpenSearch
  - 实战
  - 日志
categories:
  - OpenSearch 入门
---

通过一个 Nginx 访问日志分析案例，串联 mapping、导入、搜索、聚合与 Dashboards。

## 日志样例

```
192.168.1.10 - - [19/Aug/2026:10:00:01 +0800] "GET /api/users HTTP/1.1" 200 1234 "-" "curl/7.68"
```

## 1. 创建索引模板

```bash
PUT /_index_template/nginx-logs-template
{
  "index_patterns": ["nginx-logs-*"],
  "template": {
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "client_ip": { "type": "ip" },
        "method": { "type": "keyword" },
        "path": { "type": "keyword" },
        "status": { "type": "integer" },
        "bytes": { "type": "long" },
        "user_agent": { "type": "text" }
      }
    }
  }
}
```

## 2. Filebeat + Ingest Pipeline（或 Logstash grok）

```bash
PUT /_ingest/pipeline/nginx-pipeline
{
  "processors": [
    {
      "grok": {
        "field": "message",
        "patterns": [
          "%{IPORHOST:client_ip} - - \\[%{HTTPDATE:timestamp}\\] \"%{WORD:method} %{URIPATH:path}(?:%{URIPARAM})? HTTP/%{NUMBER:http_version}\" %{NUMBER:status:int} %{NUMBER:bytes:long}"
        ]
      }
    },
    { "date": { "field": "timestamp", "formats": ["dd/MMM/yyyy:HH:mm:ss Z"] } }
  ]
}
```

## 3. 写入测试数据

```bash
POST /nginx-logs-2026.08.19/_doc?pipeline=nginx-pipeline
{
  "message": "192.168.1.10 - - [19/Aug/2026:10:00:01 +0800] \"GET /api/users HTTP/1.1\" 200 1234 \"-\" \"curl/7.68\""
}
```

## 4. 常用查询

**5xx 错误**：
```json
{
  "query": { "range": { "status": { "gte": 500 } } }
}
```

**Top 路径**：
```json
{
  "size": 0,
  "aggs": {
    "top_paths": {
      "terms": { "field": "path", "size": 10 }
    }
  }
}
```

**每小时请求量**：
```json
{
  "size": 0,
  "aggs": {
    "req_per_hour": {
      "date_histogram": {
        "field": "@timestamp",
        "calendar_interval": "1h"
      }
    }
  }
}
```

## 5. Dashboards

- 饼图：status 分布
- 折线图：req_per_hour
- 表格：top_paths
- 过滤器：status >= 400

## 扩展练习

1. 按 client_ip 统计 Top 访问源
2. 告警：5xx 每分钟 > 10（需 Alerting 插件）
3. 保留 30 天 ISM 自动删索引

这个案例覆盖日志场景 **80% 日常需求**。
