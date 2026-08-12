---
title: OpenSearch 与 Filebeat 日志采集入门
date: 2026-08-19 12:15:00
tags:
  - OpenSearch
  - Filebeat
  - 日志
categories:
  - OpenSearch 入门
---

**Filebeat → OpenSearch** 是最常见的日志入门链路（替代 ELK 中的 Logstash）。

## 架构

```
App log file → Filebeat → OpenSearch Index → Dashboards
```

## Filebeat 配置

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/app/*.log
    fields:
      app: my-service
      env: dev
    fields_under_root: true

output.opensearch:
  hosts: ["http://localhost:9200"]
  index: "logs-my-service-%{+yyyy.MM.dd}"
  # 若开启安全：
  # username: admin
  # password: xxx

setup.template.name: "logs-my-service"
setup.template.pattern: "logs-my-service-*"
setup.ilm.enabled: false
```

```bash
filebeat setup --index-management -E output.opensearch.hosts=['http://localhost:9200']
filebeat -e
```

## 使用 Logstash（可选）

适合复杂转换（grok、mutate）：

```ruby
# logstash.conf
input { beats { port => 5044 } }

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:ts} %{LOGLEVEL:level} %{GREEDYDATA:msg}" }
  }
  date { match => ["ts", "ISO8601"] }
}

output {
  opensearch {
    hosts => ["http://localhost:9200"]
    index => "logs-parsed-%{+YYYY.MM.dd}"
  }
}
```

## 索引模板

Filebeat 可自动加载 template，或手动创建（见索引模板篇）。

## Dashboards 查看

1. Index Pattern: `logs-my-service-*`
2. Time field: `@timestamp`
3. Discover 搜索 `level:ERROR`

## 常见字段

| 字段 | 来源 |
|------|------|
| `@timestamp` | Beat 采集时间 |
| `message` | 原始日志行 |
| `host.name` | 主机名 |
| `agent.type` | filebeat |

## 排查

| 问题 | 检查 |
|------|------|
| 无数据 | Filebeat 日志、output 连通 |
| 403 | 认证、索引权限 |
| mapping 冲突 | 删旧索引或改 index 名 |

Filebeat 轻量够用；复杂 ETL 再加 Logstash 或 Flink。
