---
title: Kafka 在 Kubernetes 上的 SRE 部署
date: 2026-08-16 11:45:00
tags:
  - Kafka
  - Kubernetes
  - Strimzi
categories:
  - Kafka SRE
---

K8s 上运行 Kafka 推荐 **Strimzi Operator**，管理 Broker、Topic、User、Connect。

## Strimzi Kafka 集群

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.6.0
    replicas: 3
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
    storage:
      type: persistent-claim
      size: 500Gi
      class: fast-ssd
  zookeeper:
    replicas: 3
    storage:
      type: persistent-claim
      size: 100Gi
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

> Kafka 3.7+ 可用 KRaft 模式，Strimzi 支持 `KafkaNodePool`。

## Topic CR

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: orders
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 12
  replicas: 3
  config:
    retention.ms: 604800000
    min.insync.replicas: 2
```

## 存储要点

- **ReadWriteOnce** SSD，每 Broker 独立 PVC
- 禁止 EmptyDir 存生产数据
- 磁盘 IOPS 满足峰值写入

## 网络

- 集群内 `*.my-cluster-kafka-bootstrap:9092`
- 外部客户端用 LoadBalancer / Ingress（Strimzi Kafka Listener）

## 监控

Strimzi 内置 Prometheus metrics：

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
spec:
  kafka:
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
```

## SRE 注意

| 项 | 建议 |
|----|------|
| 滚动升级 | Operator 控制，先 ZK/KRaft 再 Broker |
| PDB | minAvailable ≥ 2 |
| 反亲和 | spread 跨 AZ |
| 扩容 | 增 PVC 或加 Broker（Strimzi 支持） |

## 检查清单

- [ ] 3 Broker + 3 ZK/KRaft
- [ ] TLS + SCRAM 开启
- [ ] Topic/User Operator 启用
- [ ] PodMonitor + Lag 告警
- [ ] 备份/MM2 方案独立于 K8s

K8s 适合 GitOps 与弹性，**磁盘与副本策略**仍是 SRE 核心。
