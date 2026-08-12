---
title: Flink 在 Kubernetes 上的 SRE 部署
date: 2026-08-18 11:45:00
tags:
  - Flink
  - Kubernetes
  - Operator
categories:
  - Flink SRE
---

**Flink Kubernetes Operator** 是云原生 Flink 生产部署的事实标准。

## Operator 安装

```bash
helm repo add flink-operator https://downloads.apache.org/flink/flink-kubernetes-operator-1.8.0/
helm install flink-kubernetes-operator flink-operator/flink-kubernetes-operator
```

## FlinkDeployment 生产模板

```yaml
apiVersion: flink.apache.org/v1beta1
kind: FlinkDeployment
metadata:
  name: orders-realtime
spec:
  image: my-registry/flink:1.19-custom
  flinkVersion: v1_19
  flinkConfiguration:
    taskmanager.numberOfTaskSlots: "4"
    state.backend: rocksdb
    state.checkpoints.dir: s3://bucket/flink/checkpoints
    execution.checkpointing.interval: "60000"
    metrics.reporters: prom
    metrics.reporter.prom.factory.class: org.apache.flink.metrics.prometheus.PrometheusReporterFactory
    metrics.reporter.prom.port: "9249"
  serviceAccount: flink
  jobManager:
    resource:
      memory: "2048m"
      cpu: 1
    replicas: 2
  taskManager:
    replicas: 4
    resource:
      memory: "8192m"
      cpu: 4
  job:
    jarURI: s3://bucket/jars/orders-job.jar
    entryClass: com.example.OrdersJob
    parallelism: 16
    upgradeMode: savepoint
    savepointTriggerNonce: 0
    state: running
  podTemplate:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: orders-realtime
                topologyKey: topology.kubernetes.io/zone
```

## Savepoint 升级

```bash
# 触发 savepoint
kubectl patch flinkdeployment orders-realtime --type=merge -p '
  {"spec":{"job":{"savepointTriggerNonce":1}}}'
# 更新 jarURI / parallelism 后 Operator 自动 savepoint-stop → restore
```

## 存储与 IRSA

```yaml
# ServiceAccount 注解 AWS IAM Role
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::xxx:role/flink-s3-access
```

## 监控

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: flink-orders
spec:
  selector:
    matchLabels:
      app: orders-realtime
  podMetricsEndpoints:
    - port: metrics
```

## SRE 注意

| 项 | 建议 |
|----|------|
| upgradeMode | 生产用 savepoint |
| PDB | minAvailable 保证 TM |
| 镜像 | Connector 预装 lib/ |
| 日志 | sidecar 或 stdout → Loki |

## 检查清单

- [ ] JM replicas ≥ 2
- [ ] Checkpoint S3 权限 IRSA
- [ ] PodMonitor + 告警
- [ ] 跨 AZ 反亲和
- [ ] savepoint 升级演练通过

K8s 部署与 **Kafka SRE（Strimzi）** 同集群时注意资源配额隔离。
