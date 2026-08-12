---
title: Volcano 集群安装与快速上手
date: 2026-08-12 19:00:00
tags:
  - Volcano
  - 安装
categories:
  - Volcano
---

从零在 Kubernetes 集群部署 Volcano，并跑通第一个 Gang Job。

## 前置条件

- Kubernetes 1.20+
- kubectl 已配置
- 可选：GPU 节点 + NVIDIA Device Plugin

## 安装 Volcano

```bash
kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/master/installer/volcano-development.yaml
```

验证：

```bash
kubectl get pods -n volcano-system
# 应看到 volcano-scheduler、volcano-controllers、volcano-admission 等 Running
```

## 创建 Queue

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: default
spec:
  weight: 1
  capability:
    cpu: "32"
    memory: 64Gi
```

```bash
kubectl apply -f queue.yaml
```

## 提交测试 Job

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: test-job
spec:
  schedulerName: volcano
  minAvailable: 3
  queue: default
  tasks:
    - replicas: 3
      name: task
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: busybox
              image: busybox
              command: ["sh", "-c", "echo Hello Volcano && sleep 30"]
```

```bash
kubectl apply -f job.yaml
kubectl get vcjob
kubectl get pods
```

3 个 Pod 应**同时**进入 Running。

## Helm 安装（可选）

```bash
helm repo add volcano-sh https://volcano-sh.github.io/volcano
helm install volcano volcano-sh/volcano -n volcano-system --create-namespace
```

## 卸载

```bash
kubectl delete -f https://raw.githubusercontent.com/volcano-sh/volcano/master/installer/volcano-development.yaml
```

## 常见问题

- **Webhook 超时**：检查 volcano-admission 与 API Server 网络
- **Pod 不调度**：确认 `schedulerName: volcano` 且 Queue 存在
- **版本不匹配**：CRD 版本与 Volcano 发行版对齐

安装完成后，即可在现有 K8s 集群上跑分布式训练 Job。
