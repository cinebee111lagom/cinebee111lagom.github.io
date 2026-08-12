---
title: Flink 监控体系：Prometheus 与 Grafana
date: 2026-08-18 10:45:00
tags:
  - Flink
  - Prometheus
  - 监控
categories:
  - Flink SRE
---

Flink 原生支持 Prometheus Reporter，配合 Grafana 构成生产监控标准栈。

## 开启 Prometheus Reporter

```yaml
# flink-conf.yaml
metrics.reporter.prom.class: org.apache.flink.metrics.prometheus.PrometheusReporter
metrics.reporter.prom.port: 9249
metrics.reporter.prom.factory.class: org.apache.flink.metrics.prometheus.PrometheusReporterFactory
```

K8s 用 PodMonitor 抓取 TM/JM 各 Pod 的 9249 端口。

## 核心指标

| 指标 | 含义 | 告警 |
|------|------|------|
| `flink_jobmanager_numRunningJobs` | 运行作业数 | 突降 P0 |
| `flink_job_lastCheckpointDuration` | Checkpoint 耗时 | > 5min P1 |
| `flink_job_lastCheckpointSize` | Checkpoint 大小 | 突增 50% |
| `flink_taskmanager_job_task_backPressuredTimeMsPerSecond` | 反压 | 持续 > 500 P1 |
| `flink_taskmanager_job_task_numRecordsInPerSecond` | 输入速率 | 突降 |
| `flink_job_numFailedCheckpoints` | 失败次数 | 连续失败 P0 |

## Consumer Lag（外部）

Flink 消费 Kafka 时，同时监控 **Kafka consumer lag**（Burrow / kafka_exporter）。

## Grafana Dashboard

- 社区：**10369** Flink Dashboard
- 关注：Checkpoint、反压、Records I/O、GC

## 日志

```yaml
# 集中采集 JM/TM stdout + log4j
# 关键：Checkpoint 失败、Exception、OutOfMemoryError
```

→ ELK/Loki，按 `jobId` 关联。

## REST API 巡检

```bash
curl http://jm:8081/jobs/overview
curl http://jm:8081/jobs/<jobId>/exceptions
curl http://jm:8081/taskmanagers
```

## 检查清单

- [ ] 每 TM/JM 暴露 Prometheus 端口
- [ ] Checkpoint 失败 P0 告警
- [ ] 反压 HIGH 持续告警
- [ ] Kafka Lag 与 Flink 指标同 Dashboard
- [ ] 告警链 Runbook

**反压 + Checkpoint + Lag** 是 Flink SRE 监控铁三角。
