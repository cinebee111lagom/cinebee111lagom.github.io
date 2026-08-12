---
title: Flink 集群部署实战：Standalone 与 YARN Application
date: 2026-08-18 09:30:00
tags:
  - Flink
  - 部署
categories:
  - Flink SRE
---

生产常见 Standalone HA（小规模）与 YARN Application（中大规模）两种部署方式。

## Standalone HA（ZooKeeper）

```yaml
# flink-conf.yaml
high-availability: zookeeper
high-availability.storageDir: hdfs:///flink/ha
high-availability.zookeeper.quorum: zk1:2181,zk2:2181,zk3:2181
high-availability.cluster-id: /flink-prod

jobmanager.rpc.address: jm1
jobmanager.memory.process.size: 2048m
taskmanager.memory.process.size: 4096m
taskmanager.numberOfTaskSlots: 4

state.backend: rocksdb
state.checkpoints.dir: s3://bucket/flink/checkpoints
state.savepoints.dir: s3://bucket/flink/savepoints
execution.checkpointing.interval: 60000
execution.checkpointing.mode: EXACTLY_ONCE
```

```bash
# 启动 JM（HA 需多个）
./bin/jobmanager.sh start
./bin/taskmanager.sh start

# Application 模式提交
./bin/flink run-application -t yarn-application \
  -Dyarn.application.name=orders-job \
  -Dtaskmanager.memory.process.size=4096m \
  -Dtaskmanager.numberOfTaskSlots=4 \
  -c com.example.OrdersJob \
  s3://bucket/jars/orders-job.jar
```

## YARN Application 关键参数

```bash
-Dyarn.application.queue=realtime
-Djobmanager.memory.process.size=2048m
-Dtaskmanager.memory.process.size=8192m
-Dtaskmanager.numberOfTaskSlots=8
-Dparallelism.default=16
-Dstate.backend=rocksdb
-Dstate.checkpoints.dir=hdfs:///flink/checkpoints
```

## 目录规划

```
/opt/flink/          # 安装目录
/var/log/flink/      # 日志
/data/flink/         # 本地 state（HashMap 后端时）
s3://bucket/flink/   # Checkpoint/Savepoint
```

## 部署检查清单

- [ ] JM HA 已配置（ZK 或 K8s native HA）
- [ ] Checkpoint 存储高可用（S3/HDFS）
- [ ] TM slot 数 × TM 数 ≥ 作业最大并行度
- [ ] 时区与 NTP 同步
- [ ] 防火墙：6123(RPC)、8081(REST)

## 常见问题

| 问题 | 解决 |
|------|------|
| TM 注册不上 | 检查 `jobmanager.rpc.address` |
| Checkpoint 写失败 | S3/HDFS 权限、路径可达 |
| YARN 资源不足 | 调 queue 配额或减 slot |

Standalone 适合 POC；**生产推荐 Application 模式** 资源隔离。
