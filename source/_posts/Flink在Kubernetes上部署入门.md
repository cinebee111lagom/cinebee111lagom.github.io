---
title: Flink 在 Kubernetes 上部署入门
date: 2026-08-17 12:45:00
tags:
  - Flink
  - Kubernetes
  - 部署
categories:
  - Flink 新手入门
---

生产环境常用 **Flink Kubernetes Operator** 或 Native K8s 模式部署，新手需了解基本流程。

## 部署模式

| 模式 | 说明 |
|------|------|
| Session | 共享集群，多作业提交 |
| Application | 一作业一集群（推荐生产） |
| Per-Job | 已废弃，用 Application 替代 |

## Native Kubernetes Application

```bash
./bin/flink run-application -t kubernetes-application \
  -Dkubernetes.cluster-id=flink-app-1 \
  -Dkubernetes.container.image=my-flink:1.19 \
  -c com.example.MyJob \
  local:///opt/flink/usrlib/my-job.jar
```

## Flink Kubernetes Operator

```yaml
apiVersion: flink.apache.org/v1beta1
kind: FlinkDeployment
metadata:
  name: orders-job
spec:
  image: my-flink:1.19
  flinkVersion: v1_19
  flinkConfiguration:
    taskmanager.numberOfTaskSlots: "4"
    state.backend: rocksdb
    state.checkpoints.dir: s3://bucket/checkpoints
  jobManager:
    resource:
      memory: "2048m"
      cpu: 1
  taskManager:
    replicas: 2
    resource:
      memory: "4096m"
      cpu: 2
  job:
    jarURI: local:///opt/flink/usrlib/orders-job.jar
    entryClass: com.example.OrdersJob
    parallelism: 8
    upgradeMode: savepoint
```

## Docker 镜像

```dockerfile
FROM flink:1.19-scala_2.12-java11
COPY target/my-job.jar /opt/flink/usrlib/
COPY lib/*.jar /opt/flink/lib/
```

## Savepoint 升级

```bash
# 触发 savepoint
flink savepoint <jobId> s3://bucket/savepoints

# 从 savepoint 启动
-Dexecution.savepoint.path=s3://bucket/savepoints/savepoint-xxx
```

## 资源配置建议

| 组件 | 起步 |
|------|------|
| JobManager | 1~2 GB |
| TaskManager | 4~8 GB，slots=CPU 核数 |
| Checkpoint 存储 | S3/HDFS，与 Pod 分离 |

## 常见问题

| 问题 | 解决 |
|------|------|
| Pod OOMKilled | 加 memory、调 RocksDB managed memory |
| 镜像缺 Connector | 打进 lib/ 或 usrlib |
| Checkpoint 失败 | 检查 S3 权限、网络 |

新手可先用 **Application 模式 + 单作业**，熟悉后再上 Operator GitOps。
