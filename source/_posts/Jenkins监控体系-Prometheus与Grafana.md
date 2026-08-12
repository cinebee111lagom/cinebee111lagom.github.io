---
title: Jenkins 监控体系：Prometheus 与 Grafana
date: 2026-08-23 10:30:00
tags:
  - Jenkins
  - Prometheus
  - 监控
categories:
  - Jenkins SRE
---

Jenkins 通过 **Prometheus Metrics Plugin** 暴露指标，接入 Grafana 与告警。

## 安装插件

- Prometheus metrics plugin
- CloudBees Disk Usage Simple（可选，磁盘）

## 暴露指标

```
https://jenkins.example.com/prometheus/
```

需配置访问权限或内网 scrape + Basic Auth。

## Prometheus 配置

```yaml
scrape_configs:
  - job_name: jenkins
    metrics_path: /prometheus
    scheme: https
    basic_auth:
      username: prometheus
      password: xxx
    static_configs:
      - targets: ["jenkins.example.com"]
```

## 核心指标

| 指标 | 含义 | 告警 |
|------|------|------|
| `jenkins_health_check_score` | 健康分 | < 1 P0 |
| `jenkins_queue_size` | 排队 Job 数 | > 20 P1 |
| `jenkins_executor_free` | 空闲 executor | = 0 持续 P1 |
| `jenkins_node_offline_value` | 节点离线 | > 0 P1 |
| `default_jenkins_builds_success_build_count_total` | 成功构建 | — |
| `default_jenkins_builds_failed_build_count_total` | 失败构建 | 突增 |

## Grafana Dashboard

- 社区 Dashboard ID：**9964** Jenkins Performance
- 面板：队列、Executor、构建率、节点状态

## 日志

```
/var/log/jenkins/jenkins.log
```

→ Filebeat → OpenSearch，关联 build number。

## 健康检查 API

```bash
curl -s https://jenkins.example.com/login | head -1
curl -s https://jenkins.example.com/api/json?tree=jobs[name,color]
```

LB 探活可用 `/login` 返回 200。

## Checklist

- [ ] Prometheus 插件已装
- [ ] scrape 内网可达
- [ ] 队列、离线节点、健康分告警
- [ ] Dashboard 按团队/Folder 分视图

监控铁三角：**队列长度 + Executor + 节点在线**。
