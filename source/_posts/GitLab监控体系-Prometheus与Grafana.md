---
title: GitLab 监控体系：Prometheus 与 Grafana
date: 2026-08-29 10:00:00
tags:
  - GitLab
  - SRE
  - Prometheus
categories:
  - GitLab SRE
---

GitLab Omnibus **内置 Prometheus**，也可 scrape 到外部监控栈。

## 启用内置 Prometheus

```ruby
# gitlab.rb
prometheus_monitoring['enable'] = true
node_exporter['enable'] = true
redis_exporter['enable'] = true
postgres_exporter['enable'] = true
gitlab_exporter['enable'] = true
```

指标默认 `:9090`（仅内网，勿公网暴露）。

## 关键指标

| 指标 | 含义 |
|------|------|
| gitlab_transaction_duration_seconds | Web 请求延迟 |
| gitlab_sidekiq_queue_size | 后台队列积压 |
| gitlab_ci_pipeline_processing_events | CI 处理量 |
| ruby_memory_bytes | Rails 内存 |
| gitaly_connections_total | Gitaly 连接 |
| pg_stat_activity_count | PG 连接数 |

## 外部 Prometheus scrape

```yaml
scrape_configs:
  - job_name: gitlab-rails
    metrics_path: /-/metrics
    scheme: https
    static_configs:
      - targets: ['gitlab.example.com']
    bearer_token: '<metrics token>'
```

**Settings → Metrics and profiling → Metrics token**

## Grafana Dashboard

- 官方：**GitLab Omnibus** dashboard（社区）
- 面板：HTTP 5xx、Sidekiq latency、Runner 队列、Gitaly RPC

## 日志

```bash
gitlab-ctl tail gitlab-rails
gitlab-ctl tail sidekiq
gitlab-ctl tail gitaly
```

接入 ELK/Loki，保留 **audit.json** 合规。

## SLI

| SLI | 来源 |
|-----|------|
| 可用性 | `/-/health` blackbox |
| API 延迟 | rails histogram |
| CI 调度 | pipeline pending 时长 |
| 错误率 | nginx 5xx |

## 反模式

- 无 Sidekiq 队列告警
- Prometheus 公网无认证
- 不监控 Gitaly 磁盘

**Sidekiq 积压 > 10k 持续 15min → P1**。
