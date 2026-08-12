---
title: Flink SRE 告警规则与值班手册
date: 2026-08-18 11:00:00
tags:
  - Flink
  - SRE
  - 告警
categories:
  - Flink SRE
---

Flink 告警需覆盖作业级、TaskManager 级与外部依赖（Kafka/S3）。

## 告警分级

| 级别 | 场景 | 响应 |
|------|------|------|
| P0 | 作业 FAILED、Checkpoint 连续失败 | 5 分钟 |
| P1 | 反压 HIGH、Lag 超阈值、JM failover | 15 分钟 |
| P2 | Checkpoint 变慢、TM 内存高 | 1 小时 |
| P3 | Savepoint 过期清理、证书续期 | 工作日 |

## Prometheus 规则示例

```yaml
groups:
  - name: flink
    rules:
      - alert: FlinkJobDown
        expr: flink_jobmanager_numRunningJobs == 0
        for: 2m
        labels:
          severity: critical

      - alert: FlinkCheckpointFailed
        expr: increase(flink_job_numFailedCheckpoints[10m]) > 2
        labels:
          severity: critical

      - alert: FlinkBackpressureHigh
        expr: flink_taskmanager_job_task_backPressuredTimeMsPerSecond > 800
        for: 10m
        labels:
          severity: warning

      - alert: FlinkCheckpointSlow
        expr: flink_job_lastCheckpointDuration > 300000
        for: 15m
        labels:
          severity: warning
```

## 值班速查

### 作业 FAILED

```bash
curl http://jm:8081/jobs/<jobId>/exceptions
# 查 stack trace → OOM / 序列化 / Sink 失败
flink run -s <last-savepoint> ...  # 从 savepoint 恢复
```

### Checkpoint 失败

- TM 日志搜 `Checkpoint expired`
- 检查 S3 限流、反压、状态膨胀
- 临时增大 `checkpoint.timeout`

### 反压严重

1. Web UI 定位瓶颈算子
2. 查 Sink（DB/Kafka）是否慢
3. 提高 Sink 并行度或批量写

### TM 丢失

```bash
curl http://jm:8081/taskmanagers
# YARN/K8s 是否 OOMKilled
kubectl describe pod <tm-pod>
```

### Kafka Lag 高

- 先区分 Flink 消费慢还是生产突增
- 对齐 Source 并行度与 Kafka 分区数

## On-Call 原则

1. 优先恢复作业（savepoint 重启）
2. 再根因，避免反复 FAIL
3. 变更必须 savepoint
4. 48h Postmortem

Lag 告警按 **Consumer Group + 作业** 分级，减少误报。
