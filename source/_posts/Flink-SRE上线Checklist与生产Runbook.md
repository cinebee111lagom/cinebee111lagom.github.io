---
title: Flink SRE 上线 Checklist 与生产 Runbook
date: 2026-08-18 13:45:00
tags:
  - Flink
  - SRE
  - Runbook
categories:
  - Flink SRE
---

## 上线 Checklist

### 架构

- [ ] Application 模式或独立 FlinkDeployment
- [ ] JM HA（≥2 副本或 ZK HA）
- [ ] Checkpoint/Savepoint 存 S3/HDFS（高可用）
- [ ] 容量压测：吞吐、Checkpoint 耗时、反压

### 配置

- [ ] EXACTLY_ONCE Checkpoint 开启
- [ ] RocksDB + 增量 Checkpoint（状态 > 10GB）
- [ ] 重启策略 configured
- [ ] 并行度与 Kafka 分区对齐
- [ ] State TTL 已评审

### 安全

- [ ] REST 8081 内网鉴权
- [ ] Kafka SASL_SSL、JDBC 凭证 Secret 化
- [ ] S3 桶私有 + 加密

### 依赖

- [ ] Kafka Topic RF=3，ACL 就绪
- [ ] Sink 端幂等或 EOS 语义确认
- [ ] Schema Registry 兼容性（若用 Avro）

### 监控

- [ ] Prometheus + Grafana
- [ ] Checkpoint 失败、反压、Lag P0/P1 告警
- [ ] 告警链 Runbook 链接
- [ ] 日志集中采集

### 变更

- [ ] Savepoint 升级流程文档化
- [ ] 回滚 savepoint 路径约定
- [ ] On-Call 轮值明确

---

## 日常 Runbook

### 作业 FAILED（P0）

```bash
curl http://jm:8081/jobs/<jobId>/exceptions
# 定位 OOM/Sink/序列化
flink run -s s3://bucket/flink/savepoints/latest ... job.jar
```

### Checkpoint 连续失败

- 查 TM 日志、S3 权限、反压
- 临时：`checkpoint.timeout` ↑，`interval` ↑
- 根因：状态膨胀 / Sink 慢

### 反压 HIGH

1. Web UI 定位算子
2. Sink 批量/并行度
3. 数据倾斜排查

### TM OOMKilled

```bash
kubectl describe pod <tm-pod>
# 增 memory / 减 slot / RocksDB managed memory 调优
```

### 计划升级

```bash
flink stop --savepointPath s3://bucket/savepoints/<version> <jobId>
flink run -s <savepoint-path> -c ... job-new.jar
# Operator: upgradeMode savepoint + savepointTriggerNonce++
```

### Kafka Lag 高

- Flink 消费慢 vs 生产突增
- Source 并行度、反压、下游 Sink

---

**Flink SRE 系列 20 篇**完结，涵盖部署、HA、Checkpoint、RocksDB、监控、反压、安全、K8s、升级、大状态、Kafka EOS、容灾与演练。建议配合 **Flink 新手入门**、**Kafka SRE** 系列对照阅读。
