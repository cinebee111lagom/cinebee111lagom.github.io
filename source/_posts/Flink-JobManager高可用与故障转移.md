---
title: Flink JobManager 高可用与故障转移
date: 2026-08-18 09:45:00
tags:
  - Flink
  - 高可用
categories:
  - Flink SRE
---

JobManager 是 Flink 大脑，单点故障会导致作业失败，生产必须 HA。

## HA 方案

| 方案 | 依赖 | 适用 |
|------|------|------|
| ZooKeeper HA | ZK 3 节点 | Standalone/YARN 传统 |
| Kubernetes HA | K8s ConfigMap/Lease | K8s Native |
| 云托管 | 平台内置 | Ververica/Confluent |

## ZK HA 配置

```yaml
high-availability: zookeeper
high-availability.storageDir: s3://bucket/flink/ha
high-availability.zookeeper.quorum: zk1:2181,zk2:2181,zk3:2181
high-availability.cluster-id: /flink-prod-cluster
rest.port: 8081
```

## 故障转移流程

```
1. Active JM 宕机
2. ZK 锁释放，Standby JM 抢主
3. 从 HA storage 恢复 JobGraph
4. 向 TM 下发 task，从最近 Checkpoint 恢复
5. 作业继续运行（at-least-once 语义下可能重复）
```

## K8s Native HA

```yaml
# FlinkDeployment
spec:
  jobManager:
    replicas: 2
    resource:
      memory: "2048m"
  flinkConfiguration:
    high-availability.type: kubernetes
    high-availability.storageDir: s3://bucket/flink/ha
    kubernetes.cluster-id: flink-prod
```

## 与 Checkpoint 关系

- JM HA **不替代** Checkpoint
- JM 切换依赖最近一次成功 Checkpoint 恢复状态
- 无 Checkpoint → 作业从 savepoint 或重启（丢状态）

## 监控

| 指标 | 告警 |
|------|------|
| `numRegisteredTaskManagers` | 低于预期 |
| `numRunningJobs` | 突降 |
| JM leader 切换事件 | 日志/ZK watch |

## 检查清单

- [ ] 至少 2 JM 实例
- [ ] HA storage 与 Checkpoint 分离路径
- [ ] ZK/K8s 自身 HA
- [ ] 定期 JM failover 演练
- [ ] REST API 负载均衡指向 active JM

**JM HA + Checkpoint 双保险**，缺一不可。
